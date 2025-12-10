import json
import re
import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import ANALYST_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT, DEBUGGER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator
from src.app.services.parsers.openapi import OpenAPIParser
from src.app.agents.batch import process_batch
from src.app.services.deduplication import DeduplicationService
from src.app.services.defects import DefectAnalysisService
from src.app.services.tools.browser import WebInspector

logger = logging.getLogger(__name__)

dedup_service = DeduplicationService()
defect_service = DefectAnalysisService()
llm_service = CloudRuLLMService()
web_inspector = WebInspector()

async def analyst_node(state: AgentState) -> Dict[str, Any]:
    logger.info("🚀 [Analyst] Node started.")
    llm = llm_service.get_model(state.get("model_name"))
    raw_input = state['user_request']
    
    # 0. Auto-Fix Check
    if "[AUTO-FIX]" in raw_input:
        logger.info("🔧 [Analyst] Detected Auto-Fix request. Redirecting to Debugger.")
        return {
            "status": ProcessingStatus.FIXING,
            "logs": ["System: Detected Auto-Fix request. Handing over to Debugger."]
        }

    # 1. RAG & Defects
    defects_context = defect_service.get_relevant_defects(raw_input)
    cached_code = dedup_service.find_similar(raw_input)
    
    if cached_code:
        logger.info("✅ [Analyst] Found exact match in RAG. Skipping generation.")
        return {
            "generated_code": cached_code,
            "status": ProcessingStatus.COMPLETED,
            "logs": ["Analyst: Found exact match in knowledge base (RAG). Skipping generation.", "System: Retrieved verified code from Vector DB."]
        }

    # 2. Parsing
    parsed_context = ""
    if "[SOURCE CODE CONTEXT" in raw_input:
        parsed_context = raw_input
    elif "http" in raw_input and "api" in raw_input.lower():
        logger.info(f"🔍 [Analyst] Parsing OpenAPI spec from URL in request.")
        parsed_context = OpenAPIParser.parse(raw_input, query=raw_input)
    else:
        parsed_context = raw_input

    # 3. Web Inspector
    url_match = re.search(r'https?://[^\s]+', raw_input)
    inspection_logs = []
    vision_context = ""
    
    if url_match and "api" not in raw_input.lower():
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
    
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"Context/Requirements:\n{parsed_context}{defects_context}{vision_context}")
    ]
    
    try:
        response = await llm.ainvoke(messages)
    except Exception as e:
        logger.error(f"❌ [Analyst] LLM Call Failed with Vision Context: {e}. Retrying WITHOUT vision context...")
        inspection_logs.append("Analyst: LLM crashed on DOM data. Retrying in blind mode...")
        # Fallback: remove vision context
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=f"Context/Requirements:\n{parsed_context}{defects_context}")
        ]
        try:
            response = await llm.ainvoke(messages)
        except Exception as e2:
            logger.error(f"❌ [Analyst] LLM Failed again: {e2}")
            raise e2

    plan = response.content
    
    t_type = TestType.API if "api" in raw_input.lower() else TestType.UI
    
    scenarios = []
    if "### SCENARIO:" in plan:
        raw_scenarios = plan.split("### SCENARIO:")
        scenarios = [s.strip() for s in raw_scenarios if s.strip()]
    
    logger.info(f"📝 [Analyst] Plan created. Scenarios detected: {len(scenarios) if len(scenarios) > 1 else 1}.")
    
    return {
        "test_plan": [str(plan)],
        "technical_context": parsed_context + vision_context,
        "scenarios": scenarios if len(scenarios) > 1 else None,
        "test_type": t_type,
        "status": ProcessingStatus.GENERATING,
        "logs": [
            f"Analyst: Plan created. Identified {len(scenarios) if len(scenarios) > 1 else 1} scenario(s). Type: {t_type}.",
            *inspection_logs
        ],
        "attempts": 0
    }


async def coder_node(state: AgentState) -> Dict[str, Any]:
    logger.info("🚀 [Coder] Node started.")
    llm = llm_service.get_model(state.get("model_name"))
    is_fixing = state.get("status") == ProcessingStatus.FIXING or state.get("validation_error") is not None
    
    if is_fixing:
        logger.info(f"🔧 [Coder/Debugger] Fixing mode activated. Attempt: {state.get('attempts', 0) + 1}")
        user_error_log = state['user_request'].replace("[AUTO-FIX]", "").strip() if "[AUTO-FIX]" in state['user_request'] else ""
        internal_error = state.get("validation_error", "")
        error_context = user_error_log if user_error_log else internal_error
        
        sys_prompt = DEBUGGER_SYSTEM_PROMPT if "[AUTO-FIX]" in state['user_request'] else FIXER_SYSTEM_PROMPT
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"ERROR LOG:\n{error_context}\n\nCODE TO FIX:\n{state['generated_code']}")
        ]
        log_msg = f"Debugger: Fixing execution errors (Attempt {state.get('attempts', 0) + 1})..."
    else:
        logger.info("💻 [Coder] Generation mode activated.")
        plan_str = "\n".join(state["test_plan"])
        tech_context = state.get("technical_context", "")
        messages = [
            SystemMessage(content=CODER_SYSTEM_PROMPT),
            HumanMessage(content=f"Technical Context:\n{tech_context}\n\nTest Plan:\n{plan_str}\n\nGenerate the full Python code now.")
        ]
        log_msg = "Coder: Generating initial code..."

    response = await llm.ainvoke(messages)
    code = str(response.content).replace("```python", "").replace("```", "").strip()
    logger.info(f"✅ [Coder] Code generated ({len(code)} chars).")

    return {
        "generated_code": code,
        "validation_error": None,
        "status": ProcessingStatus.VALIDATING,
        "attempts": state.get("attempts", 0) + 1,
        "logs": [log_msg]
    }


async def reviewer_node(state: AgentState) -> Dict[str, Any]:
    logger.info("🚀 [Reviewer] Node started. Validating code...")
    code = state["generated_code"]
    is_valid, error_msg, fixed_code = CodeValidator.validate(code)
    
    new_state = {"generated_code": fixed_code or code}

    if is_valid:
        logger.info("✅ [Reviewer] Code is VALID.")
        dedup_service.save(state['user_request'], new_state["generated_code"])
        new_state["status"] = ProcessingStatus.COMPLETED
        new_state["logs"] = ["Reviewer: Code passed checks (Auto-Fixed). Ready for dispatch.", "System: Saved to Knowledge Base."]
        return new_state
    else:
        logger.warning(f"❌ [Reviewer] Code is INVALID. Sending back to Coder. Error: {error_msg[:100]}...")
        new_state["status"] = ProcessingStatus.FIXING
        new_state["validation_error"] = error_msg
        new_state["logs"] = [f"Reviewer: Validation failed.\n{error_msg}"]
        return new_state

async def batch_node(state: AgentState) -> Dict[str, Any]:
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
