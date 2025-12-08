import json
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import ANALYST_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator
from src.app.services.parsers.openapi import OpenAPIParser
from src.app.agents.batch import process_batch
from src.app.services.deduplication import DeduplicationService

dedup_service = DeduplicationService()

llm_service = CloudRuLLMService()
llm = llm_service.get_model()


async def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyst Agent: Parses requirements, checks history of defects, and determines test strategy.
    """
    defects_context = ""
    try:
        with open("src/app/data/defects.json", "r") as f:
            defects = json.load(f)
            req_lower = state['user_request'].lower()
            relevant_defects = [d for d in defects if d['component'].lower() in req_lower or (
                'api' in req_lower and 'api' in d['component'].lower()) or
                ('calculator' in req_lower and 'calculator' in d['component'].lower())]
            
            if relevant_defects:
                defects_context = "\n\n[HISTORICAL DEFECTS - COVER THESE EDGE CASES]:\n" + "\n".join(
                    [f"- {d['description']} ({d['severity']})" for d in relevant_defects]
                )
    except Exception:
        pass

    raw_input = state['user_request']
    cached_code = dedup_service.find_similar(raw_input)
    
    if cached_code:
        return {
            "generated_code": cached_code,
            "status": ProcessingStatus.COMPLETED,
            "logs": ["Analyst: Found exact match in knowledge base (RAG). Skipping generation.", "System: Retrieved verified code from Vector DB."]
        }

    parsed_context = OpenAPIParser.parse(raw_input, query=raw_input)
    
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"Context/Requirements:\n{parsed_context}{defects_context}")
    ]
    
    response = await llm.ainvoke(messages)
    plan = response.content
    
    t_type = TestType.API if "api" in state['user_request'].lower() else TestType.UI
    
    scenarios = []
    if "### SCENARIO:" in plan:
        raw_scenarios = plan.split("### SCENARIO:")
        scenarios = [s.strip() for s in raw_scenarios if s.strip()]
    
    return {
        "test_plan": [str(plan)],
        "scenarios": scenarios if len(scenarios) > 1 else None,
        "test_type": t_type,
        "status": ProcessingStatus.GENERATING,
        "logs": [f"Analyst: Plan created. Identified {len(scenarios) if len(scenarios) > 1 else 1} scenario(s). Type: {t_type}."],
        "attempts": 0
    }


async def coder_node(state: AgentState) -> Dict[str, Any]:
    """
    Coder Agent: Generates the test code.
    Handles both initial generation and fixing based on errors.
    """
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
    Reviewer Agent: Validates the code using static analysis and pytest collection.
    """
    code = state["generated_code"]
    is_valid, error_msg = CodeValidator.validate(code)

    if is_valid:
        dedup_service.save(state['user_request'], code)
        
        return {
            "status": ProcessingStatus.COMPLETED,
            "logs": ["Reviewer: Code passed all checks! Ready for dispatch.", "System: Saved to Knowledge Base."]
        }
    else:
        return {
            "status": ProcessingStatus.FIXING,
            "validation_error": error_msg,
            "logs": [f"Reviewer: Validation failed.\n{error_msg[:200]}..."]
        }

async def batch_node(state: AgentState) -> Dict[str, Any]:
    """
    Batch Processor: Runs multiple scenarios in parallel.
    """
    scenarios = state["scenarios"]
    results = await process_batch(scenarios)
    
    combined_code = "\n\n# ==========================================\n".join(results)
    
    return {
        "generated_code": combined_code,
        "status": ProcessingStatus.COMPLETED,
        "logs": [f"Batch: Successfully generated {len(results)} tests in parallel."]
    }
