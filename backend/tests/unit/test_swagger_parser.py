import json
import pytest
from src.app.services.parsers.openapi import OpenAPIParser

# Mock Petstore Swagger (simplified)
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
        "operationId": "listPets",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "description": "How many items to return at one time (max 100)",
            "required": False,
            "schema": {
              "type": "integer",
              "format": "int32"
            }
          }
        ]
      },
      "post": {
        "summary": "Create a pet",
        "operationId": "createPets",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/Pet"
              }
            }
          },
          "required": True
        }
      }
    },
    "/pets/{petId}": {
      "get": {
        "summary": "Info for a specific pet",
        "operationId": "showPetById",
        "parameters": [
          {
            "name": "petId",
            "in": "path",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ]
      }
    }
  }
}

def test_extract_endpoints_from_json():
    """
    Test that endpoints are correctly extracted with methods and parameters.
    """
    json_content = json.dumps(PETSTORE_SWAGGER)
    summary = OpenAPIParser.parse(json_content)
    
    print(f"\nGenerated Summary:\n{summary}")

    assert "Swagger Petstore" in summary
    # Check GET /pets
    assert "GET /pets [limit]" in summary
    # Check POST /pets with Body
    assert "POST /pets [BODY]" in summary
    # Check Path Parameter
    assert "GET /pets/{petId} [petId*]" in summary

def test_parser_handles_invalid_json():
    """
    Test graceful fallback for non-json text.
    """
    text = "Just a requirement description"
    result = OpenAPIParser.parse(text)
    assert "Requirements Text: Just a requirement description" in result
