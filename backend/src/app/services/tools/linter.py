import ast
import os
import subprocess
import tempfile
from typing import Tuple


class CodeValidator:
    """
    The 'Reviewer' Agent's main tool.
    Performs a 4-stage validation pipeline:
    1. AST Parsing & Security Scan (Syntax + Safety)
    2. Allure Compliance Check (Architecture Standards)
    3. Ruff Check (Static Analysis)
    4. Pytest Collection (Import & Decorator validity)
    """

    BANNED_IMPORTS = {'os', 'subprocess', 'shutil', 'sys', 'builtins'}
    BANNED_FUNCTIONS = {'eval', 'exec', 'compile'}

    @staticmethod
    def validate(code: str) -> Tuple[bool, str]:
        # 1. AST Parsing & Security Scan
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"AST Syntax Error: {e}"

        # Security & Allure Check
        has_allure_import = False
        has_allure_decorator = False

        for node in ast.walk(tree):
            # Security: Check imports
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name in CodeValidator.BANNED_IMPORTS:
                        return False, f"Security Error: Forbidden import '{n.name}'. Generated code cannot access system internals."
                    if n.name == 'allure':
                        has_allure_import = True
            elif isinstance(node, ast.ImportFrom):
                if node.module in CodeValidator.BANNED_IMPORTS:
                    return False, f"Security Error: Forbidden import from '{node.module}'."
                if node.module == 'allure':
                    has_allure_import = True
            
            # Security: Check calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in CodeValidator.BANNED_FUNCTIONS:
                    return False, f"Security Error: Forbidden function '{node.func.id}'."

            # Allure: Check decorators
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == 'allure':
                                has_allure_decorator = True

        if not has_allure_import:
             return False, "Allure Compliance Error: 'import allure' is missing."
        
        if "allure." not in code:
             return False, "Allure Compliance Error: No Allure decorators found."

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # 2. Ruff
            ruff_res = subprocess.run(
                ["ruff", "check", tmp_path, "--select", "E,F", "--output-format", "text"],
                capture_output=True,
                text=True
            )
            if ruff_res.returncode != 0:
                return False, f"Linter Error (Ruff):\n{ruff_res.stdout}"

            # 3. Pytest Collection
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
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
