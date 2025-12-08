import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DefectAnalysisService:
    """
    Service for analyzing historical defects and providing context for test generation.
    """
    
    def __init__(self, data_path: str = "src/app/data/defects.json"):
        self.data_path = data_path
        self._defects = self._load_defects()

    def _load_defects(self) -> List[Dict[str, Any]]:
        try:
            with open(self.data_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Defects file not found at {self.data_path}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in defects file at {self.data_path}")
            return []

    def get_relevant_defects(self, query: str) -> str:
        """
        Returns a formatted string of relevant defects based on the user query.
        """
        if not self._defects:
            return ""

        req_lower = query.lower()
        relevant_defects = [
            d for d in self._defects 
            if d['component'].lower() in req_lower or 
            ('api' in req_lower and 'api' in d['component'].lower()) or
            ('calculator' in req_lower and 'calculator' in d['component'].lower())
        ]
        
        if not relevant_defects:
            return ""
            
        return "\n\n[HISTORICAL DEFECTS - COVER THESE EDGE CASES]:\n" + "\n".join(
            [f"- {d['description']} ({d['severity']})" for d in relevant_defects]
        )
