import asyncio
import re
import ast
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage

from src.app.services.llm_factory import CloudRuLLMService
from src.app.agents.prompts import CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.tools.linter import CodeValidator

llm_service = CloudRuLLMService()
llm = llm_service.get_model()

SEMAPHORE = asyncio.Semaphore(5)

async def process_single_scenario(scenario: str, index: int) -> str:
    """
    Runs the full generation loop (Code -> Validate -> Fix) for a single scenario.
    Includes Post-Processing to avoid Class Name Collisions.
    """
    async with SEMAPHORE:
        messages = [
            SystemMessage(content=CODER_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate a Pytest test for this scenario:\n{scenario}")
        ]
        
        try:
            response = await llm.ainvoke(messages)
            code = str(response.content).replace("```python", "").replace("```", "").strip()
            
            # Validation Loop
            for attempt in range(3):
                is_valid, error_msg, fixed_code = CodeValidator.validate(code)
                
                if fixed_code:
                    code = fixed_code
                
                if is_valid:
                    return _isolate_namespaces(code, index)
                
                fix_prompt = FIXER_SYSTEM_PROMPT.format(
                    error_log=error_msg,
                    code=code
                )
                response = await llm.ainvoke([
                    SystemMessage(content=CODER_SYSTEM_PROMPT),
                    HumanMessage(content=fix_prompt)
                ])
                code = str(response.content).replace("```python", "").replace("```", "").strip()
            
            final_code = _isolate_namespaces(code, index)
            return f"# FAILED TO VALIDATE AFTER 3 ATTEMPTS\n# ERROR: {error_msg}\n{final_code}"
            
        except Exception as e:
            return f"# GENERATION ERROR: {str(e)}"

def _isolate_namespaces(code: str, index: int) -> str:
    """
    Renames classes to prevent collisions using AST to find names safely,
    then Regex for replacement (simplified but safer with verified names).
    """
    suffix = f"_S{index}"
    
    try:
        tree = ast.parse(code)
        # Rename ALL classes, including Test classes, to avoid collisions in batch mode
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    except SyntaxError:
        return code

    modified_code = code
    # Sort by length desc to avoid replacing substrings
    class_names.sort(key=len, reverse=True)
    
    for name in class_names:
        # REMOVED: if "Test" in name: continue 
        # We MUST rename Test classes too because they often have generic names like TestCalculator
        
        pattern = r"\b" + name + r"\b"
        modified_code = re.sub(pattern, f"{name}{suffix}", modified_code)
        
    return modified_code

async def process_batch(scenarios: List[str]) -> List[str]:
    """
    Orchestrates parallel execution of test scenarios.
    """
    tasks = [process_single_scenario(s, i) for i, s in enumerate(scenarios)]
    results = await asyncio.gather(*tasks)
    return list(results)
