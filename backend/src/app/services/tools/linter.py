import ast
import os
import subprocess
import tempfile
from typing import Tuple, Optional, Set, List


class CodeValidator:
    """
    The 'Reviewer' Agent's main tool.
    Performs a pipeline: Auto-Fix -> Security -> Lint -> Strict Allure Compliance -> Test Collection.
    Returns: (is_valid, log, fixed_code)
    """

    BANNED_IMPORTS = {'os', 'subprocess', 'shutil', 'sys', 'builtins'}
    BANNED_FUNCTIONS = {'eval', 'exec', 'compile'}

    @staticmethod
    def validate(code: str) -> Tuple[bool, str, Optional[str]]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"AST Syntax Error: {e}", None

        # 1. Security Check
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

        # 2. Strict Allure TestOps Compliance Check
        allure_errors = CodeValidator._check_allure_compliance(tree)
        if allure_errors:
            return False, "Allure Strict Compliance Failed:\n" + "\n".join(allure_errors), code

        # 3. Formatting & Linter (Ruff)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        fixed_code = code

        try:
            # Auto-Fix import sorting and common issues
            subprocess.run(
                ["ruff", "check", tmp_path, "--fix", "--select", "E,F,I,UP,B", "--ignore", "F841"],
                capture_output=True
            )
            subprocess.run(["ruff", "format", tmp_path], capture_output=True)

            with open(tmp_path, "r") as f:
                fixed_code = f.read()

            # Strict Linting
            ruff_res = subprocess.run(
                ["ruff", "check", tmp_path, "--select", "E9,F63,F7,F82", "--output-format", "full"],
                capture_output=True,
                text=True
            )
            if ruff_res.returncode != 0:
                error_output = ruff_res.stdout or ruff_res.stderr
                return False, f"Linter Error (Ruff):\n{error_output}", fixed_code

            # 4. Pytest Collection Check
            pytest_res = subprocess.run(
                ["pytest", tmp_path, "--collect-only", "-q"],
                capture_output=True,
                text=True
            )
            if pytest_res.returncode != 0:
                return False, f"Pytest Collection Error:\n{pytest_res.stdout}\n{pytest_res.stderr}", fixed_code

            return True, "Code is valid, strict, and ready for review.", fixed_code

        except Exception as e:
            return False, f"Validation System Error: {str(e)}", fixed_code
        
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @staticmethod
    def _check_allure_compliance(tree: ast.Module) -> List[str]:
        """
        Enforces strict Allure TestOps metadata requirements via AST analysis.
        Iterates over the Module body to handle both Classes and Standalone Functions.
        """
        errors = []
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                CodeValidator._check_class(node, errors)
            elif isinstance(node, ast.FunctionDef):
                 if node.name.startswith("test_"):
                     CodeValidator._check_function(node, errors, parent_has_owner=False)
        
        return errors

    @staticmethod
    def _check_class(node: ast.ClassDef, errors: List[str]):
        class_decorators = CodeValidator._get_decorator_names(node)
        if "allure.feature" not in class_decorators:
            errors.append(f"Class '{node.name}' missing @allure.feature")
        if "allure.story" not in class_decorators:
            errors.append(f"Class '{node.name}' missing @allure.story")
        
        has_class_owner = CodeValidator._has_label(node, "owner")
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                CodeValidator._check_function(item, errors, parent_has_owner=has_class_owner)

    @staticmethod
    def _check_function(node: ast.FunctionDef, errors: List[str], parent_has_owner: bool):
        func_decorators = CodeValidator._get_decorator_names(node)
        
        if "allure.title" not in func_decorators:
            errors.append(f"Test '{node.name}' missing @allure.title")
        if "allure.tag" not in func_decorators:
            errors.append(f"Test '{node.name}' missing @allure.tag")
        if "allure.link" not in func_decorators:
            errors.append(f"Test '{node.name}' missing @allure.link (Jira)")
        if "allure.label.priority" not in func_decorators and not CodeValidator._has_label(node, "priority"):
                errors.append(f"Test '{node.name}' missing @allure.label('priority', ...)")
        
        if not parent_has_owner and not CodeValidator._has_label(node, "owner"):
            errors.append(f"Test '{node.name}' missing @allure.label('owner', ...) (checked class and function)")

    @staticmethod
    def _get_decorator_names(node: [ast.ClassDef, ast.FunctionDef]) -> Set[str]:
        decorators = set()
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                 decorators.add(f"{decorator.value.id}.{decorator.attr}")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    name = f"{decorator.func.value.id}.{decorator.func.attr}"
                    decorators.add(name)
        return decorators

    @staticmethod
    def _has_label(node: [ast.ClassDef, ast.FunctionDef], label_name: str) -> bool:
        """
        Checks for specific @allure.label("key", "value")
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.value.id == "allure" and decorator.func.attr == "label":
                    if decorator.args:
                        first_arg = decorator.args[0]
                        if isinstance(first_arg, ast.Constant) and first_arg.value == label_name:
                            return True
        return False
