import re

from src.app.services.code_analysis.schemas import ParsedEndpoint


class NodeJSParser:
	"""
	Regex-based parser for Node.js (Express, NestJS).
	"""

	def parse_file(self, file_path: str, content: str) -> list[ParsedEndpoint]:
		endpoints = []

		# --- NestJS Strategy ---
		# 1. Class Controller Prefix
		# Matches @Controller('path') or @Controller("path")
		controller_match = re.search(r"@Controller\s*\([\'\"]([^\'\"]*)[\'\"]\)", content)
		base_path = controller_match.group(1) if controller_match else ""

		# 2. Method Decorators
		# Simplified Regex:
		# 1. @Method group(1)
		# 2. (...) capture content in group(2)
		# 3. Skip whitespace/newlines
		# 4. Skip optional other decorators (starting with @, ending with ))
		# 5. Skip modifiers (public/async)
		# 6. Capture function name group(3)
		# 7. Expect open paren (

		nest_pattern = r"@(Get|Post|Put|Delete|Patch|Options|Head)\s*\(([^)]*)\)\s*(?:@[^)]+\)\s*)*(?:public|private|protected)?\s*(?:async)?\s*(\w+)\s*\("

		for match in re.finditer(nest_pattern, content, re.DOTALL):
			method = match.group(1).lower()
			raw_path = match.group(2).strip()
			func_name = match.group(3)

			# Clean up path (remove quotes)
			path_part = raw_path.strip("'\"")

			full_path = f"{base_path}/{path_part}".replace("//", "/")
			if full_path.endswith("/") and len(full_path) > 1:
				full_path = full_path.rstrip("/")

			endpoints.append(ParsedEndpoint(
				path=full_path,
				method=method,
				function_name=func_name,
				source_file=file_path,
				line_number=0,
				description="NestJS Endpoint"
			))

		# --- Express.js Strategy ---
		express_pattern = r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]"

		for match in re.finditer(express_pattern, content):
			method = match.group(1).lower()
			path = match.group(2)

			endpoints.append(ParsedEndpoint(
				path=path,
				method=method,
				function_name="anonymous",
				source_file=file_path,
				line_number=0,
				description="Express.js Route"
			))

		return endpoints
