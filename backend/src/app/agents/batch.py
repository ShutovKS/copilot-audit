import ast
import asyncio
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.agents.prompts import CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT
from src.app.services.llm_factory import CloudRuLLMService
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
            # Reverted to simple invoke without response_format
            response = await llm.ainvoke(messages)
            raw_content = str(response.content)

            # Improved code extraction from markdown blocks
            code_match = re.search(r"```python\s*([\s\S]*?)```", raw_content)
            if code_match:
                code = code_match.group(1).strip()
            else:
                # Fallback: assume the whole content is code and let the validator handle it
                code = raw_content.strip()

            # Validation Loop
            for _attempt in range(3):
                is_valid, error_msg, fixed_code = CodeValidator.validate(code)

                if fixed_code:
                    code = fixed_code

                if is_valid:
                    return _isolate_namespaces(code, index)

                # If validation fails, ask the model to fix it
                fix_prompt = FIXER_SYSTEM_PROMPT.format(
                    error_log=error_msg,
                    code=code
                )

                fix_messages = [
                    SystemMessage(content=CODER_SYSTEM_PROMPT),
                    HumanMessage(content=fix_prompt)
                ]

                # Also reverted here
                response = await llm.ainvoke(fix_messages)
                raw_content = str(response.content)

                # Use same extraction logic for the fix
                code_match = re.search(r"```python\s*([\s\S]*?)```", raw_content)
                if code_match:
                    code = code_match.group(1).strip()
                else:
                    code = raw_content.strip()

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


async def process_batch(scenarios: list[str]) -> list[str]:
	"""
	Orchestrates parallel execution of test scenarios.
	"""
	tasks = [process_single_scenario(s, i) for i, s in enumerate(scenarios)]
	results = await asyncio.gather(*tasks)
	return list(results)
