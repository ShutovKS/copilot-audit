import javalang

from src.app.services.code_analysis.schemas import ParsedEndpoint, ParsedParameter


class JavaASTParser:
	"""
	AST-based parser for Spring Boot using 'javalang'.
	Much more robust than Regex.
	"""

	def parse_file(self, file_path: str, content: str) -> list[ParsedEndpoint]:
		endpoints = []
		try:
			tree = javalang.parse.parse(content)
		except javalang.parser.JavaSyntaxError:
			return []

		for _path, node in tree.filter(javalang.tree.ClassDeclaration):
			# 1. Check Class-level @RequestMapping
			base_path = ""
			if node.annotations:
				for ann in node.annotations:
					if ann.name == 'RequestMapping' or ann.name == 'RestController':
						# Extract path from annotation args
						base_path = self._extract_path_from_annotation(ann)

			# 2. Check Methods
			for method in node.methods:
				for ann in method.annotations:
					if ann.name in ['GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping', 'PatchMapping', 'RequestMapping']:
						http_method = self._map_annotation_to_method(ann.name)
						path_part = self._extract_path_from_annotation(ann)

						full_path = f"{base_path}/{path_part}".replace("//", "/")
						if full_path.endswith("/") and len(full_path) > 1:
							full_path = full_path.rstrip("/")

						# Extract params
						params = []
						for param in method.parameters:
							p_name = param.name
							p_type = param.type.name
							params.append(ParsedParameter(name=p_name, type_hint=p_type))

						endpoints.append(ParsedEndpoint(
							path=full_path,
							method=http_method,
							function_name=method.name,
							parameters=params,
							source_file=file_path,
							line_number=method.position.line if method.position else 0,
							description=f"Spring Boot Endpoint (in {node.name})"
						))
		return endpoints

	def _extract_path_from_annotation(self, annotation) -> str:
		if not annotation.element:
			return ""

		# Case 1: Single value @GetMapping("/path")
		if isinstance(annotation.element, javalang.tree.Literal):
			return annotation.element.value.strip('"')

		# Case 2: Array @RequestMapping({ "/path" })
		if isinstance(annotation.element, list):
			if len(annotation.element) > 0 and hasattr(annotation.element[0], 'value'):
				return annotation.element[0].value.name.strip('"')  # Simplified

		# Case 3: Named arguments @GetMapping(path = "/path")
		# javalang structure varies here, keeping it simple for MVP
		return ""

	def _map_annotation_to_method(self, annotation_name: str) -> str:
		mapping = {
			'GetMapping': 'get',
			'PostMapping': 'post',
			'PutMapping': 'put',
			'DeleteMapping': 'delete',
			'PatchMapping': 'patch',
			'RequestMapping': 'any'
		}
		return mapping.get(annotation_name, 'get')
