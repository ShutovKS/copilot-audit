import json
import requests
from typing import Dict, Any, List, Optional

class OpenAPIParser:
    """
    Utility to parse OpenAPI/Swagger specs (JSON) and extract relevant context for the LLM.
    Prevents token limit overflow by summarizing endpoints.
    """

    @staticmethod
    def parse(source: str, query: Optional[str] = None) -> str:
        """
        Parses a URL or JSON string and returns a textual summary.
        Query: User request to filter relevant endpoints.
        """
        spec = {}
        
        try:
            if source.startswith("http"):
                response = requests.get(source, timeout=10)
                response.raise_for_status()
                spec = response.json()
            elif source.strip().startswith("{"):
                spec = json.loads(source)
            else:
                return f"Requirements Text: {source}"

            return OpenAPIParser._summarize_spec(spec, query)

        except Exception as e:
            return f"Error parsing OpenAPI spec: {str(e)}. Treating input as plain text requirements: {source}"

    @staticmethod
    def _summarize_spec(spec: Dict[str, Any], query: Optional[str] = None) -> str:
        """
        Extracts Paths, Methods, and Summaries.
        If query is provided, prioritizes endpoints containing query keywords.
        """
        summary = ["OpenAPI Specification Summary:"]
        
        title = spec.get("info", {}).get("title", "Unknown API")
        summary.append(f"API Title: {title}")
        
        paths = spec.get("paths", {})
        
        keywords = []
        if query:
            keywords = [w.lower() for w in query.split() if len(w) > 3]

        relevant_endpoints = []
        other_endpoints = []
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                
                desc = details.get("summary") or details.get("description", "No description")
                
                params = []
                if "parameters" in details:
                    for p in details["parameters"]:
                        name = p.get("name")
                        required = "*" if p.get("required") else ""
                        params.append(f"{name}{required}")
                
                if "requestBody" in details:
                    params.append("BODY")

                param_str = f"[{', '.join(params)}]" if params else ""
                line = f"- {method.upper()} {path} {param_str} : {desc}"
                
                is_relevant = False
                if keywords:
                    content_to_search = (path + " " + desc).lower()
                    if any(k in content_to_search for k in keywords):
                        is_relevant = True
                
                if is_relevant:
                    relevant_endpoints.append(line)
                else:
                    other_endpoints.append(line)
        
        final_list = relevant_endpoints
        remaining_slots = 25 - len(final_list)
        
        if remaining_slots > 0:
            final_list.extend(other_endpoints[:remaining_slots])
            
        summary.extend(final_list)
        
        if len(relevant_endpoints) + len(other_endpoints) > 25:
             summary.append("... (Truncated for context limit, optimized by relevance)")

        return "\n".join(summary)
