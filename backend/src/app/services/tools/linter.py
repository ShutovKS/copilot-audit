import ast
import os
import subprocess
import tempfile
from typing import Tuple


class CodeValidator:
    """
    The 'Reviewer' Agent's main tool.
    Performs a 3-stage validation pipeline:
    1. AST Parsing (Syntax)
    2. Ruff Check (Static Analysis)
    3. Pytest Collection (Import & Decorator validity)
    """

    @staticmethod
    def validate(code: str) -> Tuple[bool, str]:
        # 1. AST Parsing (Fastest, Safest way to catch SyntaxError)
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"AST Syntax Error: {e}"

        # Create temp file for execution-based checks
        # We accept risks of running code in this env for MVP
        # In Production, this should run in an isolated docker container
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # 2. Static Analysis (Ruff)
            # Checks for F (Pyflakes) and E (Pycodestyle) errors
            ruff_res = subprocess.run(
                ["ruff", "check", tmp_path, "--select", "E,F", "--output-format", "text"],
                capture_output=True,
                text=True
            )
            if ruff_res.returncode != 0:
                return False, f"Linter Error (Ruff):\n{ruff_res.stdout}"

            # 3. Pytest Collection
            # Ensures decorators, imports and fixtures are resolvable
            pytest_res = subprocess.run(
                ["pytest", tmp_path, "--collect-only", "-q"],
                capture_output=True,
                text=True
            )
            if pytest_res.returncode != 0:
                return False, f"Pytest Collection Error:\n{pytest_res.stdout}\n{pytest_res.stderr}"

            return True, "Code is valid and ready for review."

        except Exception as e:
            return False, f"Validation System Error: {str(e)}"
        
        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
