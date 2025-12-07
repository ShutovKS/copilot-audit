import json
import requests
from typing import Dict, Any, List

class OpenAPIParser:
    """
    Utility to parse OpenAPI/Swagger specs (JSON) and extract relevant context for the LLM.
    Prevents token limit overflow by summarizing endpoints.
    """

    @staticmethod
    def parse(source: str) -> str:
        """
        Parses a URL or JSON string and returns a textual summary.
        """
        spec = {}
        
        try:
            # 1. Try treating as URL
            if source.startswith("http"):
                response = requests.get(source, timeout=10)
                response.raise_for_status()
                spec = response.json()
            # 2. Try treating as JSON string
            elif source.strip().startswith("{"):
                spec = json.loads(source)
            else:
                # Not a spec, return original text
                return f"Requirements Text: {source}"

            return OpenAPIParser._summarize_spec(spec)

        except Exception as e:
            # Log error internally, but return valid text so flow doesn't break
            return f"Error parsing OpenAPI spec: {str(e)}. Treating input as plain text requirements: {source}"

    @staticmethod
    def _summarize_spec(spec: Dict[str, Any]) -> str:
        """
        Extracts Paths, Methods, and Summaries.
        """
        summary = ["OpenAPI Specification Summary:"]
        
        title = spec.get("info", {}).get("title", "Unknown API")
        summary.append(f"API Title: {title}")
        
        paths = spec.get("paths", {})
        count = 0
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                
                desc = details.get("summary") or details.get("description", "No description")
                summary.append(f"- {method.upper()} {path} : {desc}")
                count += 1
                
                # Limit context for MVP to first 20 endpoints to avoid overflow
                if count >= 20:
                    summary.append("... (Truncated for context limit)")
                    return "\n".join(summary)
        
        return "\n".join(summary)
