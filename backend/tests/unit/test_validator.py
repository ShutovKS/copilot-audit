import pytest
from unittest.mock import MagicMock, patch
from src.app.services.tools.linter import CodeValidator

@pytest.fixture
def valid_code():
    return """
import allure
import pytest

@allure.feature("Login")
def test_example():
    with allure.step("Check boolean"):
        assert True
"""

@pytest.fixture
def code_without_allure():
    return """
def test_example():
    assert True
"""

@pytest.fixture
def syntax_error_code():
    return "def test_example()\n    assert True"

def test_validate_syntax_error(syntax_error_code: str) -> None:
    """Test that AST parsing catches syntax errors."""
    is_valid, message, fixed = CodeValidator.validate(syntax_error_code)
    assert is_valid is False
    assert "AST Syntax Error" in message

def test_validate_allure_missing(code_without_allure: str) -> None:
    """Test that code without Allure decorators fails validation."""
    with patch("src.app.services.tools.linter.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        
        is_valid, message, fixed = CodeValidator.validate(code_without_allure)

        assert is_valid is False
        assert "Allure Compliance Error" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_ruff_error(mock_run: MagicMock, valid_code: str) -> None:
    """Test that linter errors are caught."""
    
    mock_fix = MagicMock()
    mock_fix.returncode = 0
    
    mock_format = MagicMock()
    mock_format.returncode = 0
    
    mock_check_fail = MagicMock()
    mock_check_fail.returncode = 1
    mock_check_fail.stdout = "Ruff error found"
    
    mock_run.side_effect = [mock_fix, mock_format, mock_check_fail]
    
    is_valid, message, fixed = CodeValidator.validate(valid_code)
    
    assert is_valid is False
    assert "Linter Error" in message
    assert "Ruff error found" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_pytest_collection_error(mock_run: MagicMock, valid_code: str) -> None:
    """Test that pytest collection errors are caught."""
    
    mock_success = MagicMock()
    mock_success.returncode = 0
    
    mock_pytest_fail = MagicMock()
    mock_pytest_fail.returncode = 1
    mock_pytest_fail.stdout = "Pytest collection failed"
    mock_pytest_fail.stderr = "Import error"
    
    mock_run.side_effect = [mock_success, mock_success, mock_success, mock_pytest_fail]
    
    is_valid, message, fixed = CodeValidator.validate(valid_code)
    
    assert is_valid is False
    assert "Pytest Collection Error" in message

@patch("src.app.services.tools.linter.subprocess.run")
def test_validate_success(mock_run: MagicMock, valid_code: str) -> None:
    """Test successful validation."""
 
    mock_success = MagicMock()
    mock_success.returncode = 0
    
    mock_run.side_effect = [mock_success, mock_success, mock_success, mock_success]
    
    is_valid, message, fixed = CodeValidator.validate(valid_code)
    
    assert is_valid is True
    assert "Code is valid" in message
