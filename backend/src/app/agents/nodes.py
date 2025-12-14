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
from src.app.services.storage import storage_service
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
	log_path = storage_service.save(
		"System: Human approval received. Continuing to code generation...",
		run_id=state["run_id"],
		extension="log"
	)
	return {
		"status": ProcessingStatus.GENERATING,
		"log_path": log_path,
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
	run_id = state.get("run_id", "unknown_run")
	logs = []

	dedup_service = DeduplicationService(embedding_function)
	memory_service = KnowledgeBaseService(embedding_function)

	# 0. Auto-Fix Check
	if "[AUTO-FIX]" in raw_input:
		logger.info("🔧 [Analyst] Detected Auto-Fix request. Redirecting to Debugger.")
		log_path = storage_service.save("System: Detected Auto-Fix request. Handing over to Debugger.", run_id, "log")
		return {
			"status": ProcessingStatus.FIXING,
			"scenarios": [],
			"log_path": log_path,
		}

	# 1. RAG & Defects
	defects_context = defect_service.get_relevant_defects(raw_input)
	memory_context = ""
	try:
		memory_context = memory_service.recall_lessons(raw_input, url=request_url)
		if memory_context:
			logger.info("🧠 [Analyst] Found relevant lessons in long-term memory.")
			logs.append("Analyst: Injected long-term memory insights into context.")
	except Exception as e:
		logger.warning(f"⚠️ [Analyst] Memory recall failed (non-fatal): {e}")

	is_follow_up = len(state.get("messages", [])) > 1
	if is_follow_up:
		logger.info("💬 [Analyst] Follow-up message detected. Bypassing RAG cache.")
		cached_code = None
	else:
		cached_code = dedup_service.find_similar(raw_input)

	if cached_code:
		logger.info("✅ [Analyst] Found exact match in RAG. Skipping generation.")
		log_path = storage_service.save(
			"Analyst: Found exact match in knowledge base.\nSystem: Retrieved verified code.",
			run_id, "log"
		)
		code_path = storage_service.save(cached_code, run_id, "py")
		return {
			"generated_code_path": code_path,
			"status": ProcessingStatus.COMPLETED,
			"log_path": log_path,
		}

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
			parsed_context = raw_input
	elif "http" in raw_input and "api" in raw_input.lower():
		logger.info("🔍 [Analyst] Parsing OpenAPI spec from URL in request.")
		parsed_context = OpenAPIParser.parse(raw_input, query=raw_input)
	else:
		parsed_context = raw_input

	# 3. Web Inspector
	url_match = re.search(r'https?://[^\s]+', raw_input)
	vision_context = ""
	if url_match and not git_url_match and "api" not in raw_input.lower():
		url = url_match.group(0)
		logger.info(f"🌍 [Analyst] Detected URL: {url}. Starting WebInspector...")
		logs.append(f"Analyst: Detected URL {url}. Inspecting page structure...")
		try:
			dom_tree = await web_inspector.inspect_page(url)
			vision_context = f"\n\n[REAL PAGE DOM STRUCTURE ({url})]:\n{dom_tree}\n\n[INSTRUCTION]: USE THESE EXACT ATTRIBUTES (id, class, testid) FOR LOCATORS."
			logger.info(f"👁️ [Analyst] DOM Tree extracted ({len(dom_tree)} chars).")
			logs.append("Analyst: Page inspection complete. DOM context acquired.")
		except Exception as e:
			logger.error(f"❌ [Analyst] WebInspector failed: {e}")
			logs.append(f"Analyst: Inspection failed: {e}")

	# 4. LLM Call
	logger.info("🧠 [Analyst] Generating Test Plan...")
	messages_for_llm = [
		SystemMessage(content=ANALYST_SYSTEM_PROMPT),
		HumanMessage(content=(
			f"Original Request: '{state['user_request']}'\n\n"
			f"Supporting Context:\n{parsed_context}{defects_context}{memory_context}{vision_context}"
		)),
		*(state["messages"][1:] if len(state.get("messages", [])) > 1 else [])
	]

	try:
		response = await llm.ainvoke(messages_for_llm)
	except Exception as e:
		logger.error(f"❌ [Analyst] LLM Call Failed: {e}. Retrying WITHOUT vision context...")
		logs.append("Analyst: LLM crashed on DOM data. Retrying in blind mode...")
		messages_for_llm[1] = HumanMessage(content=(
			f"Original Request: '{state['user_request']}'\n\n"
			f"Supporting Context:\n{parsed_context}{defects_context}{memory_context}"
		))
		try:
			response = await llm.ainvoke(messages_for_llm)
		except Exception as e2:
			logger.error(f"❌ [Analyst] LLM Failed again: {e2}")
			raise e2

	plan = response.content

	if not plan or not plan.strip():
		question = "I wasn't able to generate a test plan. Could you please clarify the task?"
		log_path = storage_service.save("Analyst: LLM returned empty plan, asking for clarification.", run_id, "log")
		return {
			"messages": [AIMessage(content=question)],
			"status": ProcessingStatus.WAITING_FOR_INPUT,
			"log_path": log_path
		}

	if plan.strip().startswith("[CLARIFICATION]"):
		question = plan.replace("[CLARIFICATION]", "").strip()
		log_path = storage_service.save("Analyst: Ambiguous request, asking for clarification.", run_id, "log")
		return {
			"messages": [AIMessage(content=question)],
			"status": ProcessingStatus.WAITING_FOR_INPUT,
			"log_path": log_path,
		}

	t_type = TestType.API if "api" in raw_input.lower() or git_url_match else TestType.UI
	scenarios = [s.strip() for s in plan.split("### SCENARIO:")[1:] if s.strip()]
	logger.info(f"📝 [Analyst] Plan created. Scenarios: {len(scenarios) if scenarios else 1}.")

	logs.append(f"Analyst: Plan created. Identified {len(scenarios) if scenarios else 1} scenario(s). Type: {t_type}.")
	logs.append("System: Waiting for human approval of the test plan...")

	# Save artifacts
	log_path = storage_service.save("\n".join(logs), run_id, "log")
	plan_path = storage_service.save(plan, run_id, "md")
	context_path = storage_service.save(parsed_context + vision_context, run_id, "txt")

	return {
		"repo_path": str(repo_path) if repo_path else None,
		"test_plan_path": plan_path,
		"technical_context_path": context_path,
		"scenarios": scenarios if len(scenarios) > 1 else None,
		"test_type": t_type,
		"status": ProcessingStatus.WAITING_FOR_APPROVAL,
		"log_path": log_path,
		"attempts": 0
	}


async def feature_coder_node(state: AgentState) -> dict[str, Any]:
	"""Generates code based on a plan, without repository interaction."""
	logger.info("💻 [Coder] Simple generation mode activated.")
	llm = llm_service.get_model(state.get("model_name"))
	run_id = state.get("run_id", "unknown_run")

	plan_str = storage_service.load(state["test_plan_path"]) if state.get("test_plan_path") else ""
	tech_context = storage_service.load(state["technical_context_path"]) if state.get("technical_context_path") else ""

	messages = [
		SystemMessage(content=CODER_SYSTEM_PROMPT),
		HumanMessage(content=f"Technical Context:\n{tech_context}\n\nTest Plan:\n{plan_str}\n\nGenerate the full Python code now.")
	]
	log_msg = "Coder: Generating initial code..."

	try:
		response = await llm.ainvoke(messages)
		code = response.content.replace("```python", "").replace("```", "").strip()
		logger.info(f"✅ [Coder] Code generated ({len(code)} chars).")

		code_path = storage_service.save(code, run_id, "py")
		log_path = storage_service.save(log_msg, run_id, "log")

		return {
			"generated_code_path": code_path,
			"validation_error": None,
			"status": ProcessingStatus.VALIDATING,
			"attempts": state.get("attempts", 0) + 1,
			"log_path": log_path,
		}
	except Exception as e:
		logger.error(f"❌ [Coder] LLM Generation Failed: {e}", exc_info=True)
		log_path = storage_service.save(f"Coder: Critical LLM Error. The AI Provider returned an error: {str(e)}", run_id, "log")
		return {"status": ProcessingStatus.FAILED, "log_path": log_path}


async def repo_explorer_node(state: AgentState) -> dict[str, Any]:
	"""Explores a repository using tools (ReAct loop) and then generates code."""
	logger.info("🛠️ [Coder/Explorer] Tool-using repository analysis mode activated.")
	llm = llm_service.get_model(state.get("model_name"))
	repo_path_str = state.get("repo_path")
	repo_path = Path(repo_path_str)
	run_id = state.get("run_id", "unknown_run")
	logs = []

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

	plan_str = storage_service.load(state["test_plan_path"]) if state.get("test_plan_path") else ""
	tech_context = storage_service.load(state["technical_context_path"]) if state.get("technical_context_path") else ""

	messages = [
		SystemMessage(content=CODER_SYSTEM_PROMPT),
		HumanMessage(
			content=f"Technical Context:\n{tech_context}\n\nTest Plan:\n{plan_str}\n\nStart by exploring the codebase using the provided tools. Read the files mentioned in the plan, then generate the full Python code.")
	]

	max_iterations = 7
	for i in range(max_iterations):
		logger.info(f"🔄 [Coder/Explorer] ReAct Iteration {i + 1}/{max_iterations}")
		response = await llm.ainvoke(messages) # Changed to llm.ainvoke from llm_with_tools.ainvoke for direct tool calls

		if not response.tool_calls:
			logger.info("✅ [Coder/Explorer] LLM provided final code. Exiting ReAct loop.")
			code = response.content.replace("```python", "").replace("```", "").strip()
			code_path = storage_service.save(code, run_id, "py")
			logs.append(f"Coder: Generated code after {i + 1} research steps.")
			log_path = storage_service.save("\n".join(logs), run_id, "log")
			return {"generated_code_path": code_path, "status": ProcessingStatus.VALIDATING,
							"log_path": log_path}

		messages.append(response)

		for tool_call in response.tool_calls:
			tool_to_call = read_file if tool_call["name"] == "read_file" else search_code
			tool_output = await tool_to_call.ainvoke(tool_call["args"])
			messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
			log_msg = f"Tool Call: {tool_call['name']}({tool_call['args']}) -> Output: {len(tool_output)} chars"
			logger.info(f"🛠️ [Coder/Explorer] {log_msg}")
			logs.append(log_msg)

	logs.append("Coder: Failed to generate code within the maximum number of tool iterations.")
	log_path = storage_service.save("\n".join(logs), run_id, "log")
	return {"status": ProcessingStatus.FAILED, "log_path": log_path}


async def debugger_node(state: AgentState) -> dict[str, Any]:
	"""Fixes code based on validation errors or execution traces."""
	logger.info(f"🔧 [Debugger] Fixing mode activated. Attempt: {state.get('attempts', 0) + 1}")
	llm = llm_service.get_model(state.get("model_name"))
	run_id = state.get("run_id", "unknown_run")
	logs = []

	previous_code = ""
	if state.get("generated_code_path"):
		previous_code = storage_service.load(state["generated_code_path"])

	is_auto_fix = state.get("task_type") == "debug_request"

	if is_auto_fix:
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
			logs.append(f"Debugger: Fixing execution errors with Trace Analysis (Attempt {state.get('attempts', 0) + 1})...")
		else:
			logger.warning("⚠️ [Debugger] Trace context not found. Falling back to simple log analysis.")
			messages = [SystemMessage(content=FIXER_SYSTEM_PROMPT),
									HumanMessage(content=f"ERROR LOG:\n{user_error_log}\n\nCODE TO FIX:\n{previous_code}")]
			logs.append(f"Debugger: Fixing with log analysis (Attempt {state.get('attempts', 0) + 1})...")
	else: # This is a validation fix from the reviewer
		error_context = state.get("validation_error", "")
		last_fix_error = error_context
		messages = [SystemMessage(content=FIXER_SYSTEM_PROMPT),
								HumanMessage(content=f"ERROR LOG:\n{error_context}\n\nCODE TO FIX:\n{previous_code}")]
		logs.append(f"Debugger: Fixing validation errors (Attempt {state.get('attempts', 0) + 1})...")

	try:
		response = await llm.ainvoke(messages)
		code = response.content.replace("```python", "").replace("```", "").strip()
		logger.info(f"✅ [Debugger] Code fixed ({len(code)} chars).")

		new_code_path = storage_service.save(code, run_id, "py")
		old_code_path = storage_service.save(previous_code, run_id, "py.old")
		log_path = storage_service.save("\n".join(logs), run_id, "log")

		update: dict[str, Any] = {
			"generated_code_path": new_code_path,
			"validation_error": None,
			"status": ProcessingStatus.VALIDATING,
			"attempts": state.get("attempts", 0) + 1,
			"log_path": log_path,
			"was_fixing": True,
			"last_fix_old_code_path": old_code_path,
			"last_fix_error": last_fix_error,
		}
		return update
	except Exception as e:
		logger.error(f"❌ [Debugger] LLM Generation Failed: {e}", exc_info=True)
		logs.append(f"Debugger: Critical LLM Error. The AI Provider returned an error: {str(e)}")
		log_path = storage_service.save("\n".join(logs), run_id, "log")
		return {"status": ProcessingStatus.FAILED, "log_path": log_path}



async def reviewer_node(state: AgentState, embedding_function=None) -> dict[str, Any]:
	logger.info("🚀 [Reviewer] Node started. Validating code...")
	run_id = state.get("run_id", "unknown_run")
	logs = []

	code = ""
	if state.get("generated_code_path"):
		code = storage_service.load(state["generated_code_path"])

	is_valid, error_msg, fixed_code = await validation_service.validate(code)

	new_state = {}
	if fixed_code:
		new_state["generated_code_path"] = storage_service.save(fixed_code, run_id, "py")
		code = fixed_code # Use fixed code for subsequent steps

	dedup_service = DeduplicationService(embedding_function)
	memory_service = KnowledgeBaseService(embedding_function)

	# If static analysis passed, and it's a UI test, do a live locator check
	if is_valid and state.get("test_type") == TestType.UI:
		logger.info("🔬 [Reviewer] Static analysis passed. Performing locator dry run...")
		logs.append("Reviewer: Static analysis passed. Performing locator dry run...")

		# 1. Extract Locators
		locators = re.findall(r'page\.locator\("([^"]+)"\)', code)

		# 2. Extract URL from technical context
		tech_context = ""
		if state.get("technical_context_path"):
			tech_context = storage_service.load(state["technical_context_path"])
		url_match = re.search(r'https?://[^\s]+', tech_context)

		if locators and url_match:
			url = url_match.group(0)
			missing_locators = await web_inspector.check_locators_exist(url, locators)

			if missing_locators:
				logger.warning(f"❌ [Reviewer] Locator dry run FAILED. Missing: {missing_locators}")
				is_valid = False
				error_msg = f"Locator Dry Run Failed: The following locators were not found on page {url}: {missing_locators}. Please find the correct locators in the DOM and fix the code."
		else:
			logger.info("✅ [Reviewer] No locators to check or no URL found. Skipping dry run.")
			logs.append("Reviewer: No locators to check or no URL found. Skipping dry run.")


	if is_valid:
		logger.info("✅ [Reviewer] Code is VALID.")

		# Learning loop: if we just succeeded after fixing, extract + store a compact lesson.
		if state.get("was_fixing"):
			try:
				new_code = code # This is the fixed code now
				old_code = ""
				if state.get("last_fix_old_code_path"):
					old_code = storage_service.load(state["last_fix_old_code_path"])
				error_log = state.get("last_fix_error") or ""

				user_request = state.get("user_request", "")
				url = (
					_extract_goto_url_from_code(new_code)
					or _extract_first_url(tech_context)
					or _extract_first_url(user_request)
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
					logs.append("Reviewer: Stored lesson to long-term memory.")
			except Exception as e:
				logger.warning(f"⚠️ [Reviewer] Failed to store lesson (non-fatal): {e}")
				logs.append(f"Reviewer: Failed to store lesson (non-fatal): {e}")

		dedup_service.save(state['user_request'], code) # code is the (potentially fixed) generated code
		new_state["status"] = ProcessingStatus.COMPLETED
		ai_message_content = (f"I have generated the following code:\n```python\n{code}\n```\n\n"
		                      f"What would you like to do next?")
		new_state["messages"] = state.get("messages", []) + [AIMessage(content=ai_message_content)]
		logs.extend(["Reviewer: Code passed all checks (Static + Dry Run). Ready for dispatch.",
								 "System: Saved to Knowledge Base."])
		new_state["log_path"] = storage_service.save("\n".join(logs), run_id, "log")
		return {**state, **new_state} # Merge current state with new state
	else:
		logger.warning(f"❌ [Reviewer] Code is INVALID. Sending back to Coder. Error: {error_msg[:200]}...")
		logs.append(f"Reviewer: Validation failed.\n{error_msg}")
		new_state["status"] = ProcessingStatus.FIXING
		new_state["validation_error"] = error_msg
		new_state["log_path"] = storage_service.save("\n".join(logs), run_id, "log")
		return {**state, **new_state}


async def batch_node(state: AgentState) -> dict[str, Any]:
	logger.info("🚀 [Batch] Starting parallel processing...")
	run_id = state.get("run_id", "unknown_run")
	scenarios = state["scenarios"]
	results = await process_batch(scenarios)
	combined_code = "\n\n# ==========================================\n".join(results)
	logger.info(f"✅ [Batch] Completed {len(results)} scenarios.")

	code_path = storage_service.save(combined_code, run_id, "py")
	log_path = storage_service.save(f"Batch: Successfully generated {len(results)} tests in parallel.", run_id, "log")

	return {
		"generated_code_path": code_path,
		"status": ProcessingStatus.COMPLETED,
		"log_path": log_path,
	}


async def final_output_node(state: AgentState) -> dict[str, Any]:
    """
    A final node to ensure the last state is explicitly sent to the client.
    """
    logger.info("✅ [Finalizer] Graph complete. Streaming final state.")
    run_id = state.get("run_id", "unknown_run")

    final_message = state.get("messages", [])

    if not final_message:
        generated_code = ""
        if state.get("generated_code_path"):
            generated_code = storage_service.load(state["generated_code_path"])

        if generated_code:
            final_message_content = (
                f"I have generated the following code:\n```python\n{generated_code}\n```\n\n"
                f"What would you like to do next?"
            )
        else:
            final_message_content = "The process has completed. What would you like to do next?"
        final_message = [AIMessage(content=final_message_content)]

    log_path = storage_service.save("System: All tasks complete. Final output dispatched.", run_id, "log")
    return {
        "status": ProcessingStatus.COMPLETED,
        "generated_code_path": state.get("generated_code_path", ""),
        "messages": final_message,
        "log_path": log_path,
    }
