import json
import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from src.app.agents.batch import process_batch
from src.app.agents.prompts import (
	ANALYST_SYSTEM_PROMPT,
	CODER_SYSTEM_PROMPT,
	DEBUGGER_SYSTEM_PROMPT,
	FIXER_SYSTEM_PROMPT,
	ROUTER_SYSTEM_PROMPT,
)
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.domain.state import AgentState
from src.app.services.deduplication import DeduplicationService
from src.app.services.defects import DefectAnalysisService
from src.app.services.llm_factory import CloudRuLLMService
from src.app.services.memory import KnowledgeBaseService
from src.app.services.parsers.openapi import OpenAPIParser
from src.app.services.tools.browser import WebInspector
from src.app.services.tools.codebase_navigator import CodebaseNavigator
from src.app.services.tools.trace_inspector import TraceInspector
from src.app.services.validator import ValidationService

logger = logging.getLogger(__name__)

defect_service = DefectAnalysisService()
llm_service = CloudRuLLMService()
web_inspector = WebInspector()
trace_inspector = TraceInspector()
codebase_navigator = CodebaseNavigator()
# This service will be instantiated on-demand inside the node
# as it holds a reference to the Docker client.
validation_service = ValidationService()



async def human_approval_node(state: AgentState) -> dict[str, Any]:
	"""HITL gate: executed only after a human approves/resumes the graph.

	The actual pause is configured via `interrupt_before=["human_approval"]` during compilation.
	This node keeps the graph explicit (`Analyst -> human_approval -> Coder`) and avoids
	interrupting reviewer retry loops or debug flows.
	"""
	# Keep this node minimal to avoid accidentally overwriting state.
	return {
		"status": ProcessingStatus.GENERATING,
		"logs": ["System: Human approval received. Continuing to code generation..."]
	}


_URL_RE = re.compile(r"https?://[^\s]+")


def _extract_first_url(text: str | None) -> str | None:
	if not text:
		return None
	m = _URL_RE.search(text)
	return m.group(0) if m else None


def _extract_goto_url_from_code(code: str | None) -> str | None:
	"""Best-effort extraction of the target URL from Playwright code."""
	if not code:
		return None
	m = re.search(r"page\.goto\(\s*['\"]([^'\"]+)['\"]", code)
	return m.group(1) if m else None


def _extract_fix_summary_from_code(code: str | None) -> str | None:
	if not code:
		return None
	# Prefer an explicit one-liner produced by the debugger/fixer prompts.
	m = re.search(r"^\s*#\s*(?:FIX_SUMMARY|LESSON)\s*:\s*(.+?)\s*$", code, flags=re.MULTILINE)
	if not m:
		return None
	return m.group(1).strip() or None


def _truncate(text: str, limit: int) -> str:
	if len(text) <= limit:
		return text
	return text[:limit] + "\n...<truncated>..."


async def router_node(state: AgentState) -> dict[str, Any]:
	"""
	Classifies the user request and routes to the appropriate workflow.
	"""
	logger.info("🚀 [Router] Classifying user request...")
	# Use a fast model for routing
	llm = llm_service.get_model(model_name="Qwen/Qwen3-Next-80B-A3B-Instruct")

	prompt = ROUTER_SYSTEM_PROMPT + f"\nUser Request: \"{state['user_request']}\""

	try:
		response = await llm.ainvoke(prompt)
		# Clean up potential markdown formatting
		cleaned_response = response.content.replace("```json", "").replace("```", "").strip()
		result = json.loads(cleaned_response)
		task_type = result.get("task_type", "ui_test_gen")  # Default to UI test gen

		logger.info(f"✅ [Router] Classified task as: {task_type}")

		update = {"task_type": task_type}
		if task_type == "debug_request":
			update["status"] = ProcessingStatus.FIXING
			update["was_fixing"] = True

		return update

	except (json.JSONDecodeError, Exception) as e:
		logger.error(f"❌ [Router] Failed to classify request: {e}. Defaulting to 'analyst'.")
		return {"task_type": "ui_test_gen"}


async def analyst_node(state: AgentState, embedding_function=None) -> dict[str, Any]:
	logger.info("🚀 [Analyst] Node started.")
	llm = llm_service.get_model(state.get("model_name"))
	raw_input = state['user_request']
	request_url = _extract_first_url(raw_input)

	dedup_service = DeduplicationService(embedding_function)
	memory_service = KnowledgeBaseService(embedding_function)

	# 0. Auto-Fix Check (This is now handled by the router, but we keep it as a fallback)
	if "[AUTO-FIX]" in raw_input:
		logger.info("🔧 [Analyst] Detected Auto-Fix request. Redirecting to Debugger.")
		return {
			"status": ProcessingStatus.FIXING,
			"scenarios": [],
			"logs": ["System: Detected Auto-Fix request. Handing over to Debugger."]
		}

	# 1. RAG & Defects
	defects_context = defect_service.get_relevant_defects(raw_input)
	memory_context = ""
	try:
		memory_context = memory_service.recall_lessons(raw_input, url=request_url)
		if memory_context:
			logger.info("🧠 [Analyst] Found relevant lessons in long-term memory.")
	except Exception as e:
		logger.warning(f"⚠️ [Analyst] Memory recall failed (non-fatal): {e}")

	# Bypass cache for follow-up messages to allow for interactive fixes
	is_follow_up = len(state.get("messages", [])) > 1
	if is_follow_up:
		logger.info("💬 [Analyst] Follow-up message detected. Bypassing RAG cache.")
		cached_code = None
	else:
		cached_code = dedup_service.find_similar(raw_input)

	if cached_code:
		logger.info("✅ [Analyst] Found exact match in RAG. Skipping generation.")
		return {"generated_code": cached_code, "status": ProcessingStatus.COMPLETED,
						"logs": ["Analyst: Found exact match in knowledge base.", "System: Retrieved verified code."]}

	# 2. Context Parsing
	parsed_context = ""
	repo_path = None
	git_url_match = re.search(r'https?://[^\s]+\.git', raw_input)

	if "[SOURCE CODE CONTEXT" in raw_input:
		parsed_context = raw_input
	elif git_url_match:
		repo_url = git_url_match.group(0)
		logger.info(f"🐙 [Analyst] Detected Git repository: {repo_url}")
		try:
			repo_path = codebase_navigator.clone_repo(repo_url)
			file_tree = codebase_navigator.get_file_tree(repo_path)
			parsed_context = f"[SOURCE CODE REPOSITORY]\nURL: {repo_url}\n\n[FILE TREE]\n{file_tree}"
			logger.info("✅ [Analyst] Cloned repo and generated file tree.")
		except Exception as e:
			logger.error(f"❌ [Analyst] Failed to process git repository: {e}")
			# Fallback to just using the URL
			parsed_context = raw_input
	elif "http" in raw_input and "api" in raw_input.lower():
		logger.info("🔍 [Analyst] Parsing OpenAPI spec from URL in request.")
		parsed_context = OpenAPIParser.parse(raw_input, query=raw_input)
	else:
		parsed_context = raw_input

	# 3. Web Inspector (for UI tests not related to git repos)
	url_match = re.search(r'https?://[^\s]+', raw_input)
	inspection_logs = []
	vision_context = ""

	if url_match and not git_url_match and "api" not in raw_input.lower():
		url = url_match.group(0)
		logger.info(f"🌍 [Analyst] Detected URL: {url}. Starting WebInspector...")
		inspection_logs.append(f"Analyst: Detected URL {url}. Inspecting page structure...")
		try:
			dom_tree = await web_inspector.inspect_page(url)
			vision_context = f"\n\n[REAL PAGE DOM STRUCTURE ({url})]:\n{dom_tree}\n\n[INSTRUCTION]: USE THESE EXACT ATTRIBUTES (id, class, testid) FOR LOCATORS."
			logger.info(f"👁️ [Analyst] DOM Tree extracted ({len(dom_tree)} chars).")
			inspection_logs.append("Analyst: Page inspection complete. DOM context acquired.")
		except Exception as e:
			logger.error(f"❌ [Analyst] WebInspector failed: {e}")
			inspection_logs.append(f"Analyst: Inspection failed: {e}")

	# 4. LLM Call with Fallback
	logger.info("🧠 [Analyst] Generating Test Plan...")

	# This is the list of messages we will send to the LLM
	messages_for_llm = []

	# The system prompt should always be first.
	messages_for_llm.append(SystemMessage(content=ANALYST_SYSTEM_PROMPT))

	# The first user message is special; it contains the core request.
	# We will transform it into a message with all the rich context we parsed.
	first_user_message_content = state["user_request"]  # This was set by chat.py
	rich_context_content = (
		f"Original Request: '{first_user_message_content}'\n\n"
		f"Supporting Context:\n{parsed_context}{defects_context}{memory_context}{vision_context}"
	)
	messages_for_llm.append(HumanMessage(content=rich_context_content))

	# Now, append the rest of the conversation, which includes the AI's questions and the user's subsequent answers.
	# The full history is in `state["messages"]`. The first message in this list is the original user request.
	# We have already processed it, so we skip it.
	if len(state["messages"]) > 1:
		messages_for_llm.extend(state["messages"][1:])


	try:
		response = await llm.ainvoke(messages_for_llm)
	except Exception as e:
		logger.error(f"❌ [Analyst] LLM Call Failed with Vision Context: {e}. Retrying WITHOUT vision context...")
		inspection_logs.append("Analyst: LLM crashed on DOM data. Retrying in blind mode...")
		# Remove vision_context for the retry
		rich_context_content = (
			f"Original Request: '{first_user_message_content}'\n\n"
			f"Supporting Context:\n{parsed_context}{defects_context}{memory_context}"
		)
		messages_for_llm[1] = HumanMessage(content=rich_context_content) # Update the human message
		try:
			response = await llm.ainvoke(messages_for_llm)
		except Exception as e2:
			logger.error(f"❌ [Analyst] LLM Failed again: {e2}")
			raise e2

	plan = response.content

	# NEW: Check for empty or whitespace-only plan
	if not plan or not plan.strip():
		logger.warning("⚠️ [Analyst] LLM returned an empty plan. Asking for clarification.")
		question = "I wasn't able to generate a test plan from the provided context. Could you please clarify the task or provide more details about what needs to be tested?"
		return {
			"messages": [AIMessage(content=question)],
			"status": ProcessingStatus.WAITING_FOR_INPUT,
			"logs": ["Analyst: The LLM failed to generate a plan, asking for user clarification."]
		}

	# AMBIGUITY CHECK
	if plan.strip().startswith("[CLARIFICATION]"):
		logger.info("⚠️ [Analyst] Ambiguous request. Asking for user clarification.")
		question = plan.replace("[CLARIFICATION]", "").strip()
		return {
			"messages": [AIMessage(content=question)],
			"status": ProcessingStatus.WAITING_FOR_INPUT,
			"logs": ["Analyst: The request is ambiguous, asking for user clarification."]
		}

	t_type = TestType.API if "api" in raw_input.lower() or git_url_match else TestType.UI

	scenarios = []
	scenario_marker = "### SCENARIO:"
	# IMPORTANT: treat as multi-scenario only if there are 2+ scenario blocks.
	# A single marker is often used as a header/template and must NOT force batch mode.
	if plan.count(scenario_marker) >= 2:
		raw_scenarios = plan.split(scenario_marker)[1:]
		scenarios = [s.strip() for s in raw_scenarios if s.strip()]

	logger.info(f"📝 [Analyst] Plan created. Scenarios detected: {len(scenarios) if len(scenarios) > 1 else 1}.")

	return {
		"repo_path": str(repo_path) if repo_path else None,
		"test_plan": [str(plan)],
		"technical_context": parsed_context + vision_context,
		"scenarios": scenarios if len(scenarios) > 1 else None,
		"test_type": t_type,
		# HITL: stop after we have a plan and wait for explicit human approval.
		"status": ProcessingStatus.WAITING_FOR_APPROVAL,
		"logs": [
			f"Analyst: Plan created. Identified {len(scenarios) if len(scenarios) > 1 else 1} scenario(s). Type: {t_type}.",
			*( ["Analyst: Injected long-term memory insights into context."] if memory_context else [] ),
			*inspection_logs,
			"System: Waiting for human approval of the test plan..."
		],
		"attempts": 0
	}


async def feature_coder_node(state: AgentState) -> dict[str, Any]:
	"""Generates code based on a plan, without repository interaction."""
	logger.info("💻 [Coder] Simple generation mode activated.")
	llm = llm_service.get_model(state.get("model_name"))
	plan_str = "\n".join(state["test_plan"])
	tech_context = state.get("technical_context", "")
	messages = [
		SystemMessage(content=CODER_SYSTEM_PROMPT),
		HumanMessage(content=f"Technical Context:\n{tech_context}\n\nTest Plan:\n{plan_str}\n\nGenerate the full Python code now.")
	]
	log_msg = "Coder: Generating initial code..."

	try:
		response = await llm.ainvoke(messages)
		code = response.content.replace("```python", "").replace("```", "").strip()
		logger.info(f"✅ [Coder] Code generated ({len(code)} chars).")

		return {
			"generated_code": code,
			"validation_error": None,
			"status": ProcessingStatus.VALIDATING,
			"attempts": state.get("attempts", 0) + 1,
			"logs": [log_msg],
		}
	except Exception as e:
		logger.error(f"❌ [Coder] LLM Generation Failed: {e}", exc_info=True)
		return {"status": ProcessingStatus.FAILED,
						"logs": [f"Coder: Critical LLM Error. The AI Provider returned an error: {str(e)}"]}


async def repo_explorer_node(state: AgentState) -> dict[str, Any]:
	"""Explores a repository using tools (ReAct loop) and then generates code."""
	logger.info("🛠️ [Coder/Explorer] Tool-using repository analysis mode activated.")
	llm = llm_service.get_model(state.get("model_name"))
	repo_path_str = state.get("repo_path")
	repo_path = Path(repo_path_str)

	@tool
	async def read_file(file_path: str) -> str:
		"""Reads the content of a specific file within the cloned repository."""
		full_path = repo_path / file_path
		return codebase_navigator.read_file_content(full_path)

	@tool
	async def search_code(query: str) -> str:
		"""Searches for a string or regex query within the cloned repository."""
		return codebase_navigator.search_in_codebase(repo_path, query)

	llm_with_tools = llm.bind_tools([read_file, search_code])

	plan_str = "\n".join(state["test_plan"])
	tech_context = state.get("technical_context", "")

	messages = [
		SystemMessage(content=CODER_SYSTEM_PROMPT),
		HumanMessage(
			content=f"Technical Context:\n{tech_context}\n\nTest Plan:\n{plan_str}\n\nStart by exploring the codebase using the provided tools. Read the files mentioned in the plan, then generate the full Python code.")
	]

	max_iterations = 7
	for i in range(max_iterations):
		logger.info(f"🔄 [Coder/Explorer] ReAct Iteration {i + 1}/{max_iterations}")
		response = await llm_with_tools.ainvoke(messages)

		if not response.tool_calls:
			logger.info("✅ [Coder/Explorer] LLM provided final code. Exiting ReAct loop.")
			code = response.content.replace("```python", "").replace("```", "").strip()
			return {"generated_code": code, "status": ProcessingStatus.VALIDATING,
							"logs": [f"Coder: Generated code after {i + 1} research steps."]}

		messages.append(response)

		for tool_call in response.tool_calls:
			tool_to_call = read_file if tool_call["name"] == "read_file" else search_code
			tool_output = await tool_to_call.ainvoke(tool_call["args"])
			messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
			log_msg = f"Tool Call: {tool_call['name']}({tool_call['args']}) -> Output: {len(tool_output)} chars"
			logger.info(f"🛠️ [Coder/Explorer] {log_msg}")

	return {"status": ProcessingStatus.FAILED,
					"logs": ["Coder: Failed to generate code within the maximum number of tool iterations."]}


async def debugger_node(state: AgentState) -> dict[str, Any]:
	"""Fixes code based on validation errors or execution traces."""
	logger.info(f"🔧 [Debugger] Fixing mode activated. Attempt: {state.get('attempts', 0) + 1}")
	llm = llm_service.get_model(state.get("model_name"))
	previous_code = state.get("generated_code", "")
	is_auto_fix = state.get("task_type") == "debug_request"

	if is_auto_fix:
		run_id = state.get("run_id")
		# The original error is now expected to be in "user_request" for the auto-fix flow
		user_error_log = state['user_request'].replace("[AUTO-FIX]", "").strip()
		last_fix_error = user_error_log

		context = trace_inspector.get_failure_context(run_id, user_error_log)
		if context:
			logger.info("✅ [Debugger] Trace Inspector context found. Using rich debugging.")
			human_prompt = DEBUGGER_SYSTEM_PROMPT.format(
				original_error=user_error_log,
				summary=context.get("summary", "N/A"),
				network_errors="\n".join(context.get("network_errors", []) or ["None"]),
				console_logs="\n".join(context.get("console_logs", []) or ["None"]),
				dom_snapshot=context.get("dom_snapshot", "N/A"),
				selector=context.get("summary", "").split("'")[1] if "'" in context.get("summary", "") else "N/A"
			)
			messages = [HumanMessage(content=human_prompt)]
			log_msg = f"Debugger: Fixing execution errors with Trace Analysis (Attempt {state.get('attempts', 0) + 1})..."
		else:
			logger.warning("⚠️ [Debugger] Trace context not found. Falling back to simple log analysis.")
			messages = [SystemMessage(content=FIXER_SYSTEM_PROMPT),
									HumanMessage(content=f"ERROR LOG:\n{user_error_log}\n\nCODE TO FIX:\n{state['generated_code']}")]
			log_msg = f"Debugger: Fixing with log analysis (Attempt {state.get('attempts', 0) + 1})..."
	else: # This is a validation fix from the reviewer
		error_context = state.get("validation_error", "")
		last_fix_error = error_context
		messages = [SystemMessage(content=FIXER_SYSTEM_PROMPT),
								HumanMessage(content=f"ERROR LOG:\n{error_context}\n\nCODE TO FIX:\n{state['generated_code']}")]
		log_msg = f"Debugger: Fixing validation errors (Attempt {state.get('attempts', 0) + 1})..."

	try:
		response = await llm.ainvoke(messages)
		code = response.content.replace("```python", "").replace("```", "").strip()
		logger.info(f"✅ [Debugger] Code fixed ({len(code)} chars).")

		update: dict[str, Any] = {
			"generated_code": code,
			"validation_error": None,
			"status": ProcessingStatus.VALIDATING,
			"attempts": state.get("attempts", 0) + 1,
			"logs": [log_msg],
			"was_fixing": True,
			"last_fix_old_code": previous_code,
			"last_fix_error": last_fix_error,
		}
		return update
	except Exception as e:
		logger.error(f"❌ [Debugger] LLM Generation Failed: {e}", exc_info=True)
		return {"status": ProcessingStatus.FAILED,
						"logs": [f"Debugger: Critical LLM Error. The AI Provider returned an error: {str(e)}"]}



async def reviewer_node(state: AgentState, embedding_function=None) -> dict[str, Any]:
	logger.info("🚀 [Reviewer] Node started. Validating code...")
	code = state["generated_code"]
	is_valid, error_msg, fixed_code = await validation_service.validate(code)

	new_state = {"generated_code": fixed_code or code}
	dedup_service = DeduplicationService(embedding_function)
	memory_service = KnowledgeBaseService(embedding_function)

	# If static analysis passed, and it's a UI test, do a live locator check
	if is_valid and state.get("test_type") == TestType.UI:
		logger.info("🔬 [Reviewer] Static analysis passed. Performing locator dry run...")

		# 1. Extract Locators
		locators = re.findall(r'page\.locator\("([^"]+)"\)', code)

		# 2. Extract URL from technical context
		url_match = re.search(r'https?://[^\s]+', state.get("technical_context", ""))

		if locators and url_match:
			url = url_match.group(0)
			missing_locators = await web_inspector.check_locators_exist(url, locators)

			if missing_locators:
				logger.warning(f"❌ [Reviewer] Locator dry run FAILED. Missing: {missing_locators}")
				is_valid = False
				error_msg = f"Locator Dry Run Failed: The following locators were not found on page {url}: {missing_locators}. Please find the correct locators in the DOM and fix the code."
		else:
			logger.info("✅ [Reviewer] No locators to check or no URL found. Skipping dry run.")

	if is_valid:
		logger.info("✅ [Reviewer] Code is VALID.")

		# Learning loop: if we just succeeded after fixing, extract + store a compact lesson.
		if state.get("was_fixing"):
			try:
				new_code = new_state["generated_code"]
				old_code = state.get("last_fix_old_code") or ""
				error_log = state.get("last_fix_error") or ""

				url = (
					_extract_goto_url_from_code(new_code)
					or _extract_first_url(state.get("technical_context", ""))
					or _extract_first_url(state.get("user_request", ""))
				)

				fix_summary = _extract_fix_summary_from_code(new_code)
				if not fix_summary:
					# Best-effort LLM lesson extraction (non-blocking / non-fatal).
					lesson_llm = llm_service.get_model(model_name="Qwen/Qwen3-Next-80B-A3B-Instruct")
					lesson_prompt = (
						"The test passed after a fix. Summarize the TECHNICAL LESSON in ONE sentence. "
						"Focus on selectors/locators, waits/timeouts, modals/overlays, auth, redirects. "
						"Return only the sentence, no quotes, no markdown.\n\n"
						f"Original error:\n{_truncate(error_log, 1500)}\n\n"
						f"Old code (truncated):\n{_truncate(old_code, 4000)}\n\n"
						f"New code (truncated):\n{_truncate(new_code, 4000)}\n"
					)
					lesson_resp = await lesson_llm.ainvoke(lesson_prompt)
					fix_summary = str(getattr(lesson_resp, "content", "") or "").strip()

				if fix_summary:
					memory_service.learn_lesson(url=url, original_error=error_log, fix_summary=fix_summary)
					logger.info("🧠 [Reviewer] Stored lesson to long-term memory.")
			except Exception as e:
				logger.warning(f"⚠️ [Reviewer] Failed to store lesson (non-fatal): {e}")

		dedup_service.save(state['user_request'], new_state["generated_code"])
		new_state["status"] = ProcessingStatus.COMPLETED
		ai_message_content = (f"I have generated the following code:\n```python\n{new_state['generated_code']}\n```\n\n"
		                      f"What would you like to do next?")
		new_state["messages"] = state.get("messages", []) + [AIMessage(content=ai_message_content)]
		new_state["logs"] = ["Reviewer: Code passed all checks (Static + Dry Run). Ready for dispatch.",
												 "System: Saved to Knowledge Base."]
		return new_state
	else:
		logger.warning(f"❌ [Reviewer] Code is INVALID. Sending back to Coder. Error: {error_msg[:200]}...")
		new_state["status"] = ProcessingStatus.FIXING
		new_state["validation_error"] = error_msg
		new_state["logs"] = [f"Reviewer: Validation failed.\n{error_msg}"]
		return new_state


async def batch_node(state: AgentState) -> dict[str, Any]:
	logger.info("🚀 [Batch] Starting parallel processing...")
	scenarios = state["scenarios"]
	results = await process_batch(scenarios)
	combined_code = "\n\n# ==========================================\n".join(results)
	logger.info(f"✅ [Batch] Completed {len(results)} scenarios.")

	return {
		"generated_code": combined_code,
		"status": ProcessingStatus.COMPLETED,
		"logs": [f"Batch: Successfully generated {len(results)} tests in parallel."]
	}


async def final_output_node(state: AgentState) -> dict[str, Any]:
    """
    A final node to ensure the last state is explicitly sent to the client.
    """
    logger.info("✅ [Finalizer] Graph complete. Streaming final state.")

    # Check if a final message has already been set by a previous node (e.g., reviewer)
    final_message = state.get("messages", [])

    # If no message is set, create a default one.
    if not final_message:
        generated_code = state.get("generated_code", "")
        if generated_code:
            final_message_content = (
                f"I have generated the following code:\n```python\n{generated_code}\n```\n\n"
                f"What would you like to do next?"
            )
        else:
            final_message_content = "The process has completed. What would you like to do next?"
        final_message = [AIMessage(content=final_message_content)]

    return {
        "status": ProcessingStatus.COMPLETED,
        "generated_code": state.get("generated_code", ""),
        "messages": final_message,
        "logs": ["System: All tasks complete. Final output dispatched."],
    }
