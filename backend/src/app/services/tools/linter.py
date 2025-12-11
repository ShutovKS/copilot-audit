import ast
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class CodeValidator:
	BANNED_IMPORTS = {'os', 'subprocess', 'shutil', 'sys', 'builtins'}
	BANNED_FUNCTIONS = {'eval', 'exec', 'compile'}

	@staticmethod
	def validate(code: str) -> tuple[bool, str, str | None]:
		logger.debug("🔍 [Linter] Starting validation...")
		try:
			tree = ast.parse(code)
		except SyntaxError as e:
			logger.warning(f"❌ [Linter] Syntax Error: {e}")
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

		# 2. Allure Decorator Compliance
		allure_errors = CodeValidator._check_allure_compliance(tree)
		if allure_errors:
			logger.warning(f"⚠️ [Linter] Allure violations found: {len(allure_errors)}")
			return False, "Allure Strict Compliance Failed:\n" + "\n".join(allure_errors), code

		# 3. POM Consistency Check
		pom_errors = CodeValidator._check_pom_consistency(tree)
		if pom_errors:
			logger.warning(f"⚠️ [Linter] POM violations found: {len(pom_errors)}")
			return False, "Page Object Model Violation:\n" + "\n".join(pom_errors), code

		# 4. Linter & Formatting (Ruff)
		with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
			tmp.write(code)
			tmp_path = tmp.name

		fixed_code = code

		try:
			subprocess.run(
				["ruff", "check", tmp_path, "--fix", "--select", "E,F,I,UP,B", "--ignore", "F841"],
				capture_output=True,
				encoding="utf-8"
			)
			subprocess.run(["ruff", "format", tmp_path], capture_output=True, encoding="utf-8")

			with open(tmp_path, encoding="utf-8") as f:
				fixed_code = f.read()

			ruff_res = subprocess.run(
				["ruff", "check", tmp_path, "--select", "E9,F63,F7,F82", "--output-format", "full"],
				capture_output=True,
				text=True,
				encoding="utf-8"
			)
			if ruff_res.returncode != 0:
				error_output = ruff_res.stdout or ruff_res.stderr
				logger.warning(f"⚠️ [Linter] Ruff check failed:\n{error_output[:200]}...")
				return False, f"Linter Error (Ruff):\n{error_output}", fixed_code

			# 5. Pytest Collection
			pytest_res = subprocess.run(
				["pytest", tmp_path, "--collect-only", "-q"],
				capture_output=True,
				text=True,
				encoding="utf-8"
			)
			if pytest_res.returncode != 0:
				logger.warning("⚠️ [Linter] Pytest Collection failed.")
				return False, f"Pytest Collection Error:\n{pytest_res.stdout}\n{pytest_res.stderr}", fixed_code

			logger.info("✅ [Linter] Code valid.")
			return True, "Code is valid, strict, and ready for review.", fixed_code

		except Exception as e:
			logger.error(f"❌ [Linter] System Error: {e}")
			return False, f"Validation System Error: {str(e)}", fixed_code

		finally:
			if os.path.exists(tmp_path):
				os.remove(tmp_path)

	# ... (Helper methods remain same, but I need to include them to avoid truncation)
	@staticmethod
	def _check_pom_consistency(tree: ast.Module) -> list[str]:
		errors = []
		class_registry: dict[str, set[str]] = {}
		for node in tree.body:
			if isinstance(node, ast.ClassDef):
				methods = set()
				for item in node.body:
					if isinstance(item, ast.FunctionDef):
						methods.add(item.name)
				class_registry[node.name] = methods

		for node in tree.body:
			if isinstance(node, ast.ClassDef):
				for item in node.body:
					if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
						CodeValidator._verify_function_body(item, class_registry, errors)
		return errors

	@staticmethod
	def _verify_function_body(func_node: ast.FunctionDef, registry: dict[str, set[str]], errors: list[str]):
		var_types: dict[str, str] = {}
		for stmt in func_node.body:
			if isinstance(stmt, ast.Assign):
				if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
					class_name = stmt.value.func.id
					if class_name in registry:
						for target in stmt.targets:
							if isinstance(target, ast.Name):
								var_types[target.id] = class_name
			for child in ast.walk(stmt):
				if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
					if isinstance(child.func.value, ast.Name) and child.func.value.id in var_types:
						var_name = child.func.value.id
						method_name = child.func.attr
						class_type = var_types[var_name]
						if method_name not in registry[class_type]:
							errors.append(
								f"POM Violation in '{func_node.name}': Method '{method_name}' called on '{var_name}' but is NOT defined in class '{class_type}'.")

	@staticmethod
	def _check_allure_compliance(tree: ast.Module) -> list[str]:
		errors = []
		for node in tree.body:
			if isinstance(node, ast.ClassDef):
				CodeValidator._check_class(node, errors)
			elif isinstance(node, ast.FunctionDef):
				if node.name.startswith("test_"):
					CodeValidator._check_function(node, errors, parent_has_owner=False)
		return errors

	@staticmethod
	def _check_class(node: ast.ClassDef, errors: list[str]):
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
	def _check_function(node: ast.FunctionDef, errors: list[str], parent_has_owner: bool):
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
			errors.append(f"Test '{node.name}' missing @allure.label('owner', ...)")

	@staticmethod
	def _get_decorator_names(node: ast.ClassDef | ast.FunctionDef) -> set[str]:  # Updated type hint to use |
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
	def _has_label(node: ast.ClassDef | ast.FunctionDef, label_name: str) -> bool:  # Updated type hint to use |
		for decorator in node.decorator_list:
			if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
				if decorator.func.value.id == "allure" and decorator.func.attr == "label":
					if decorator.args:
						first_arg = decorator.args[0]
						if isinstance(first_arg, ast.Constant) and first_arg.value == label_name:
							return True
		return False
