from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import ANALYST_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator
from src.app.services.parsers.openapi import OpenAPIParser

# Initialize Service once
llm_service = CloudRuLLMService()
llm = llm_service.get_model()


async def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyst Agent: Parses requirements (Smart Parsing) and determines test strategy.
    """
    # Smart Parsing Logic
    raw_input = state['user_request']
    parsed_context = OpenAPIParser.parse(raw_input)
    
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"Context/Requirements:\n{parsed_context}")
    ]
    
    response = await llm.ainvoke(messages)
    plan = response.content
    
    # Simple heuristic to determine type (can be improved with structured output)
    t_type = TestType.API if "api" in state['user_request'].lower() else TestType.UI
    
    return {
        "test_plan": [str(plan)],
        "test_type": t_type,
        "status": ProcessingStatus.GENERATING,
        "logs": [f"Analyst: Plan created. Type identified as {t_type}."]
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
    
    # Clean up markdown if LLM adds it despite instructions
    code = code.replace("```python", "").replace("```", "").strip()

    return {
        "generated_code": code,
        "validation_error": None, # Reset error as we have a new candidate
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
        return {
            "status": ProcessingStatus.COMPLETED,
            "logs": ["Reviewer: Code passed all checks! Ready for dispatch."]
        }
    else:
        return {
            "status": ProcessingStatus.FIXING,
            "validation_error": error_msg,
            "logs": [f"Reviewer: Validation failed.\n{error_msg[:200]}..."]
        }
