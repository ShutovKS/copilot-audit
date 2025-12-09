import json
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import ANALYST_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator
from src.app.services.parsers.openapi import OpenAPIParser
from src.app.agents.batch import process_batch
from src.app.services.deduplication import DeduplicationService
from src.app.services.defects import DefectAnalysisService

# Initialize Services
dedup_service = DeduplicationService()
defect_service = DefectAnalysisService()
llm_service = CloudRuLLMService()


async def analyst_node(state: AgentState) -> Dict[str, Any]:
    # Dynamic LLM Init
    llm = llm_service.get_model(state.get("model_name"))
    raw_input = state['user_request']
    
    # 0. Load Historical Defects
    defects_context = defect_service.get_relevant_defects(raw_input)

    # 1. Check Deduplication (Cache)
    cached_code = dedup_service.find_similar(raw_input)
    
    if cached_code:
        return {
            "generated_code": cached_code,
            "status": ProcessingStatus.COMPLETED,
            "logs": ["Analyst: Found exact match in knowledge base (RAG). Skipping generation.", "System: Retrieved verified code from Vector DB."]
        }

    # 2. Smart Parsing Logic
    parsed_context = OpenAPIParser.parse(raw_input, query=raw_input)
    
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"Context/Requirements:\n{parsed_context}{defects_context}")
    ]
    
    response = await llm.ainvoke(messages)
    plan = response.content
    
    t_type = TestType.API if "api" in raw_input.lower() else TestType.UI
    
    scenarios = []
    if "### SCENARIO:" in plan:
        raw_scenarios = plan.split("### SCENARIO:")
        scenarios = [s.strip() for s in raw_scenarios if s.strip()]
    
    return {
        "test_plan": [str(plan)],
        "scenarios": scenarios if len(scenarios) > 1 else None,
        "test_type": t_type,
        "status": ProcessingStatus.GENERATING,
        "logs": [f"Analyst: Plan created. Identified {len(scenarios) if len(scenarios) > 1 else 1} scenario(s). Type: {t_type}. Used model: {llm.model_name}"],
        "attempts": 0
    }


async def coder_node(state: AgentState) -> Dict[str, Any]:
    llm = llm_service.get_model(state.get("model_name"))
    is_fixing = state.get("validation_error") is not None
    
    if is_fixing:
        prompt = FIXER_SYSTEM_PROMPT.format(
            error_log=state["validation_error"],
            code=state["generated_code"]
        )
        log_msg = f"Coder: Fixing errors (Attempt {state.get('attempts', 0) + 1})..."
    else:
        plan_str = "\n".join(state["test_plan"])
        prompt = f"Test Plan:\n{plan_str}\n\nGenerate the full Python code now."
        log_msg = "Coder: Generating initial code..."

    messages = [
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = await llm.ainvoke(messages)
    code = str(response.content)
    code = code.replace("```python", "").replace("```", "").strip()

    return {
        "generated_code": code,
        "validation_error": None,
        "status": ProcessingStatus.VALIDATING,
        "attempts": state.get("attempts", 0) + 1,
        "logs": [log_msg]
    }


async def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """
    Reviewer Agent: Validates the code AND Auto-Fixes it.
    """
    code = state["generated_code"]
    # Validate returns (is_valid, msg, fixed_code)
    is_valid, error_msg, fixed_code = CodeValidator.validate(code)
    
    # Always update code with the fixed version (formatting, imports)
    new_state = {"generated_code": fixed_code or code}

    if is_valid:
        dedup_service.save(state['user_request'], new_state["generated_code"])
        new_state["status"] = ProcessingStatus.COMPLETED
        new_state["logs"] = ["Reviewer: Code passed checks (Auto-Fixed). Ready for dispatch.", "System: Saved to Knowledge Base."]
        return new_state
    else:
        new_state["status"] = ProcessingStatus.FIXING
        new_state["validation_error"] = error_msg
        new_state["logs"] = [f"Reviewer: Validation failed.\n{error_msg}"]
        return new_state

async def batch_node(state: AgentState) -> Dict[str, Any]:
    scenarios = state["scenarios"]
    results = await process_batch(scenarios)
    combined_code = "\n\n# ==========================================\n".join(results)
    
    return {
        "generated_code": combined_code,
        "status": ProcessingStatus.COMPLETED,
        "logs": [f"Batch: Successfully generated {len(results)} tests in parallel."]
    }
