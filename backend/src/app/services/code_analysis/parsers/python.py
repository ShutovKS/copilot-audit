import ast
import os
from typing import List, Optional
from src.app.services.code_analysis.schemas import ParsedEndpoint, ParsedParameter

class FastAPIParser:
    """
    Native Python AST parser for FastAPI/Starlette applications.
    Extracts routes from @app.get(), @router.post(), etc.
    """

    HTTP_METHODS = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head'}

    def parse_file(self, file_path: str, content: str) -> List[ParsedEndpoint]:
        endpoints = []
        try:
            tree = ast.parse(content)
            
            # We need to track router prefixes if defined at module level (not implemented deep recursion yet)
            # Simple visitor for now
            visitor = FastAPIVisitor(file_path)
            visitor.visit(tree)
            endpoints.extend(visitor.endpoints)

        except SyntaxError:
            pass # Skip invalid python files
            
        return endpoints

class FastAPIVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.endpoints: List[ParsedEndpoint] = []
        self.router_prefix = ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)

    def _visit_func(self, node):
        # Check decorators for routing info
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                # Case: @app.get("/path") or @router.post("/path")
                method_name = decorator.func.attr
                if method_name in FastAPIParser.HTTP_METHODS:
                    self._extract_endpoint(node, decorator, method_name)

    def _extract_endpoint(self, node, decorator: ast.Call, method: str):
        path = "/"
        # Check positional args
        if decorator.args:
            if isinstance(decorator.args[0], ast.Constant):
                path = decorator.args[0].value
        # Check keyword args (path="...")
        elif decorator.keywords:
            for kw in decorator.keywords:
                if kw.arg == "path" and isinstance(kw.value, ast.Constant):
                    path = kw.value.value
                    break
        
        # Normalize empty path to root
        if not path:
            path = "/"
        
        # Extract docstring and enrich with filename context
        docstring = ast.get_docstring(node)
        if not docstring:
            # Heuristic: Use filename as hint for router prefix
            # e.g. src/api/routes/users.py -> [Context: users.py]
            fname = os.path.basename(self.filename)
            docstring = f"[Context: Defined in {fname}]"

        # Extract parameters
        params = []
        if node.args:
            for arg in node.args.args:
                if arg.arg == "self": continue
                
                p_type = None
                if arg.annotation:
                    p_type = self._get_annotation_str(arg.annotation)
                
                params.append(ParsedParameter(
                    name=arg.arg,
                    type_hint=p_type,
                    required=True # Simplified
                ))

        self.endpoints.append(ParsedEndpoint(
            path=path,
            method=method,
            function_name=node.name,
            description=docstring,
            parameters=params,
            source_file=self.filename,
            line_number=node.lineno
        ))

    def _get_annotation_str(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id}.{node.attr}" # type: ignore
        elif isinstance(node, ast.Subscript):
             # Handle List[str], Optional[int]
             value = self._get_annotation_str(node.value)
             slice_val = self._get_annotation_str(node.slice) if hasattr(node, "slice") else "Any"
             return f"{value}[{slice_val}]"
        return "Any"
