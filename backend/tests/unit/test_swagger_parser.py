import json
import pytest
from unittest.mock import MagicMock, patch
from src.app.services.parsers.openapi import OpenAPIParser

PETSTORE_SWAGGER = {
  "openapi": "3.0.0",
  "info": {
    "title": "Swagger Petstore",
    "version": "1.0.0"
  },
  "paths": {
    "/pets": {
      "get": {
        "summary": "List all pets",
        "parameters": [
          {"name": "limit", "in": "query", "required": False}
        ]
      }
    }
  }
}

def test_extract_endpoints_from_json() -> None:
    """Test valid JSON parsing."""
    json_content = json.dumps(PETSTORE_SWAGGER)
    summary = OpenAPIParser.parse(json_content)
    
    assert "Swagger Petstore" in summary
    assert "GET /pets [limit]" in summary

def test_parser_handles_invalid_json() -> None:
    """Test graceful fallback for non-json text."""
    text = "Simple text requirements"
    result = OpenAPIParser.parse(text)
    assert "Requirements Text: Simple text requirements" in result

@patch("src.app.services.parsers.openapi.requests.get")
def test_parse_from_url_success(mock_get: MagicMock) -> None:
    """Test downloading spec from URL."""
    mock_response = MagicMock()
    mock_response.json.return_value = PETSTORE_SWAGGER
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    url = "http://example.com/swagger.json"
    summary = OpenAPIParser.parse(url)
    
    mock_get.assert_called_once_with(url, timeout=10)
    assert "Swagger Petstore" in summary

@patch("src.app.services.parsers.openapi.requests.get")
def test_parse_from_url_failure(mock_get: MagicMock) -> None:
    """Test handling of network errors."""
    mock_get.side_effect = Exception("Network Error")
    
    url = "http://example.com/broken.json"
    result = OpenAPIParser.parse(url)
    
    assert "Error parsing OpenAPI spec" in result
    assert "Treating input as plain text" in result
