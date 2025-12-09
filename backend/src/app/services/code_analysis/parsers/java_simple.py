import re
from typing import List
from src.app.services.code_analysis.schemas import ParsedEndpoint, ParsedParameter

class JavaSpringParser:
    """
    Regex-based parser for Spring Boot Controllers.
    Fallback for when Tree-Sitter is not available.
    """

    def parse_file(self, file_path: str, content: str) -> List[ParsedEndpoint]:
        endpoints = []
        
        # 1. Find class-level @RequestMapping
        class_mapping = re.search(r'@RequestMapping\(["\']([^"\']+)["\']\)', content)
        base_path = class_mapping.group(1) if class_mapping else ""

        # 2. Find methods with @Get/Post/Put/DeleteMapping
        # Regex looks for annotation, then optional details, then method signature
        pattern = r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(?:\s*["\']([^"\']*)["\']\s*\).*?public\s+\w+\s+(\w+)\s*\(([^)]*)\)'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            http_verb = match.group(1).lower()
            path_part = match.group(2)
            func_name = match.group(3)
            args_str = match.group(4)
            
            full_path = f"{base_path}/{path_part}".replace("//", "/")
            
            params = []
            if args_str:
                # Naive param parsing
                # e.g. "@PathVariable String id, @RequestBody User user"
                arg_list = args_str.split(",")
                for arg in arg_list:
                    parts = arg.strip().split()
                    if len(parts) >= 2:
                        p_name = parts[-1]
                        p_type = parts[-2]
                        params.append(ParsedParameter(name=p_name, type_hint=p_type))
            
            endpoints.append(ParsedEndpoint(
                path=full_path,
                method=http_verb,
                function_name=func_name,
                parameters=params,
                source_file=file_path,
                line_number=0 # Regex doesn't easily track lines
            ))
            
        return endpoints
