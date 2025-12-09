import asyncio
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator

llm_service = CloudRuLLMService()
llm = llm_service.get_model()

SEMAPHORE = asyncio.Semaphore(5)

async def process_single_scenario(scenario: str) -> str:
    """
    Runs the full generation loop (Code -> Validate -> Fix) for a single scenario.
    """
    async with SEMAPHORE:
        messages = [
            SystemMessage(content=CODER_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate a Pytest test for this scenario:\n{scenario}")
        ]
        
        try:
            response = await llm.ainvoke(messages)
            code = str(response.content).replace("```python", "").replace("```", "").strip()
            
            for attempt in range(3):
                is_valid, error_msg, fixed_code = CodeValidator.validate(code)
                
                if fixed_code:
                    code = fixed_code
                
                if is_valid:
                    return code
                
                fix_prompt = FIXER_SYSTEM_PROMPT.format(
                    error_log=error_msg,
                    code=code
                )
                response = await llm.ainvoke([
                    SystemMessage(content=CODER_SYSTEM_PROMPT),
                    HumanMessage(content=fix_prompt)
                ])
                code = str(response.content).replace("```python", "").replace("```", "").strip()
            
            return f"# FAILED TO VALIDATE AFTER 3 ATTEMPTS\n# ERROR: {error_msg}\n{code}"
            
        except Exception as e:
            return f"# GENERATION ERROR: {str(e)}"

async def process_batch(scenarios: List[str]) -> List[str]:
    """
    Orchestrates parallel execution of test scenarios.
    """
    tasks = [process_single_scenario(s) for s in scenarios]
    results = await asyncio.gather(*tasks)
    return list(results)
