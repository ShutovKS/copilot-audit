import ast
import os
import subprocess
import tempfile
from typing import Tuple, Optional


class CodeValidator:
    """
    The 'Reviewer' Agent's main tool.
    Performs a pipeline: Auto-Fix -> Security -> Lint -> Test Collection.
    Returns: (is_valid, log, fixed_code)
    """

    BANNED_IMPORTS = {'os', 'subprocess', 'shutil', 'sys', 'builtins'}
    BANNED_FUNCTIONS = {'eval', 'exec', 'compile'}

    @staticmethod
    def validate(code: str) -> Tuple[bool, str, Optional[str]]:
        # 1. AST Parsing & Security Scan (Before fixing, safety first)
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"AST Syntax Error: {e}", None

        # Security Check
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name in CodeValidator.BANNED_IMPORTS:
                        return False, f"Security Error: Forbidden import '{n.name}'.", None
            elif isinstance(node, ast.ImportFrom):
                if node.module in CodeValidator.BANNED_IMPORTS:
                    return False, f"Security Error: Forbidden import from '{node.module}'.", None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in CodeValidator.BANNED_FUNCTIONS:
                    return False, f"Security Error: Forbidden function '{node.func.id}'.", None

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        fixed_code = code

        try:
            # 2. Auto-Fix (Ruff)
            # Added UP (pyupgrade) to modernize code and I (isort) to sort imports
            subprocess.run(
                ["ruff", "check", tmp_path, "--fix", "--select", "E,F,I,UP,B", "--ignore", "F841"],
                capture_output=True
            )
            # Auto-Format (PEP-8)
            subprocess.run(["ruff", "format", tmp_path], capture_output=True)

            # Read back fixed code
            with open(tmp_path, "r") as f:
                fixed_code = f.read()

            # 3. Allure Check (on fixed code)
            if "import allure" not in fixed_code and "from allure" not in fixed_code:
                 return False, "Allure Compliance Error: 'import allure' is missing.", fixed_code
            if "allure." not in fixed_code and "@allure" not in fixed_code:
                 return False, "Allure Compliance Error: No Allure decorators found.", fixed_code

            # 4. Final Validation (Strict)
            # Only check for syntax errors (E9), undefined names (F821), and other fatal errors.
            ruff_res = subprocess.run(
                ["ruff", "check", tmp_path, "--select", "E9,F63,F7,F82", "--output-format", "full"],
                capture_output=True,
                text=True
            )
            if ruff_res.returncode != 0:
                error_output = ruff_res.stdout or ruff_res.stderr
                return False, f"Linter Error (Ruff):\n{error_output}", fixed_code

            # 5. Pytest Collection
            pytest_res = subprocess.run(
                ["pytest", tmp_path, "--collect-only", "-q"],
                capture_output=True,
                text=True
            )
            if pytest_res.returncode != 0:
                return False, f"Pytest Collection Error:\n{pytest_res.stdout}\n{pytest_res.stderr}", fixed_code

            return True, "Code is valid and ready for review.", fixed_code

        except Exception as e:
            return False, f"Validation System Error: {str(e)}", fixed_code
        
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
