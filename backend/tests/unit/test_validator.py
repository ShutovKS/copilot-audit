import pytest
from unittest.mock import MagicMock, patch
from src.app.services.tools.linter import CodeValidator

@pytest.fixture
def valid_code():
    return "def test_example():\n    assert True"

@pytest.fixture
def syntax_error_code():
    return "def test_example()\n    assert True"

def test_validate_syntax_error(syntax_error_code: str) -> None:
    """Test that AST parsing catches syntax errors."""
    is_valid, message = CodeValidator.validate(syntax_error_code)
    assert is_valid is False
    assert "AST Syntax Error" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_ruff_error(mock_run: MagicMock, valid_code: str) -> None:
    """Test that linter errors are caught."""
    mock_ruff_response = MagicMock()
    mock_ruff_response.returncode = 1
    mock_ruff_response.stdout = "Ruff error found"
    
    mock_run.side_effect = [mock_ruff_response]
    
    is_valid, message = CodeValidator.validate(valid_code)
    
    assert is_valid is False
    assert "Linter Error" in message
    assert "Ruff error found" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_pytest_collection_error(mock_run: MagicMock, valid_code: str) -> None:
    """Test that pytest collection errors are caught."""
    mock_ruff_response = MagicMock()
    mock_ruff_response.returncode = 0
    
    mock_pytest_response = MagicMock()
    mock_pytest_response.returncode = 1
    mock_pytest_response.stdout = "Pytest collection failed"
    mock_pytest_response.stderr = "Import error"
    
    mock_run.side_effect = [mock_ruff_response, mock_pytest_response]
    
    is_valid, message = CodeValidator.validate(valid_code)
    
    assert is_valid is False
    assert "Pytest Collection Error" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_success(mock_run: MagicMock, valid_code: str) -> None:
    """Test successful validation."""
    mock_success = MagicMock()
    mock_success.returncode = 0
    
    mock_run.side_effect = [mock_success, mock_success]
    
    is_valid, message = CodeValidator.validate(valid_code)
    
    assert is_valid is True
    assert "Code is valid" in message
