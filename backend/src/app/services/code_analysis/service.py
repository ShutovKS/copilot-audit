import os
import shutil
import subprocess
import tempfile
import logging
from typing import List, Optional
from urllib.parse import urlparse, urlunparse
from src.app.services.code_analysis.schemas import ParsedEndpoint
from src.app.services.code_analysis.parsers.python import FastAPIParser
from src.app.services.code_analysis.parsers.java_ast import JavaASTParser
from src.app.services.code_analysis.parsers.java_simple import JavaSpringParser
from src.app.services.code_analysis.parsers.js_ts import NodeJSParser

logger = logging.getLogger(__name__)

class CodeAnalysisService:
    """
    Facade for analyzing source code from various sources (Local, Zip, Git).
    """

    def analyze_project(self, root_path: str) -> List[ParsedEndpoint]:
        endpoints = []
        
        for root, _, files in os.walk(root_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                if file.endswith(".py"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        parser = FastAPIParser()
                        endpoints.extend(parser.parse_file(file_path, content))
                
                elif file.endswith(".java"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if "@RestController" in content or "@Controller" in content:
                            # Strategy: Try AST first (High Precision), Fallback to Regex (Robustness)
                            try:
                                ast_parser = JavaASTParser()
                                ast_results = ast_parser.parse_file(file_path, content)
                                if ast_results:
                                    endpoints.extend(ast_results)
                                else:
                                    raise ValueError("AST returned no results")
                            except Exception as e:
                                logger.warning(f"Java AST failed for {file_path}: {e}. Falling back to Regex.")
                                regex_parser = JavaSpringParser()
                                endpoints.extend(regex_parser.parse_file(file_path, content))
                            
                elif file.endswith(".js") or file.endswith(".ts"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        parser = NodeJSParser()
                        endpoints.extend(parser.parse_file(file_path, content))
                
        return endpoints

    def format_for_llm(self, endpoints: List[ParsedEndpoint]) -> str:
        if not endpoints:
            return "No endpoints found in source code."
            
        summary = ["Source Code Analysis (Reverse Engineered API):"]
        for ep in endpoints:
            summary.append(ep.to_string())
            
        return "\n".join(summary)

    def clone_and_analyze(self, repo_url: str, token: Optional[str] = None) -> List[ParsedEndpoint]:
        """
        Clones a Git repository (public or private) and analyzes it.
        """
        if not repo_url.startswith("http"):
            raise ValueError("Invalid Git URL. Must start with http/https")
            
        final_url = repo_url
        
        if token:
            # Inject token into URL: https://oauth2:TOKEN@domain.com/repo.git
            parsed = urlparse(repo_url)
            netloc = f"oauth2:{token}@{parsed.netloc}"
            final_url = urlunparse(parsed._replace(netloc=netloc))

        with tempfile.TemporaryDirectory() as temp_dir:
            safe_log_url = repo_url  # Don't log the token version
            logger.info(f"Cloning {safe_log_url} to {temp_dir}...")
            
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", final_url, temp_dir],
                    check=True,
                    capture_output=True
                )
                return self.analyze_project(temp_dir)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode('utf-8')
                # Sanitize error message to hide token if it leaked
                if token and token in error_msg:
                    error_msg = error_msg.replace(token, "***TOKEN***")
                
                logger.error(f"Git clone failed: {error_msg}")
                raise Exception(f"Failed to clone repository: {error_msg}")
