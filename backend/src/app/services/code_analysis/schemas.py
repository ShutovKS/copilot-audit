from typing import List, Optional
from pydantic import BaseModel, Field

class ParsedParameter(BaseModel):
    name: str
    type_hint: Optional[str] = None
    source: str = "query"  # query, path, body, header
    required: bool = True

class ParsedEndpoint(BaseModel):
    path: str
    method: str
    function_name: str
    description: Optional[str] = None
    parameters: List[ParsedParameter] = []
    return_type: Optional[str] = None
    source_file: str
    line_number: int

    def to_string(self) -> str:
        """Returns a string representation suitable for LLM context."""
        params_str = ", ".join([f"{p.name}:{p.type_hint}" for p in self.parameters])
        return f"- {self.method.upper()} {self.path} ({params_str}) -> {self.return_type} : {self.description or 'No docstring'}"
