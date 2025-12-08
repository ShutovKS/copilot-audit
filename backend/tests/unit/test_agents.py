import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.app.domain.state import AgentState
from src.app.domain.enums import ProcessingStatus, TestType
from src.app.agents.nodes import analyst_node, coder_node, reviewer_node

@pytest.fixture
def mock_state():
    return {
        "user_request": "Create login test",
        "messages": [],
        "status": ProcessingStatus.IDLE,
        "test_type": None,
        "attempts": 0,
        "test_plan": [],
        "generated_code": "",
        "logs": []
    }

@pytest.mark.asyncio
@patch("src.app.agents.nodes.llm")
@patch("src.app.agents.nodes.dedup_service")
@patch("builtins.open", new_callable=MagicMock)
async def test_analyst_node(mock_open, mock_dedup, mock_llm, mock_state):
    """Test Analyst node logic."""
    mock_dedup.find_similar.return_value = None
    
    mock_response = MagicMock()
    mock_response.content = "1. Open Page\n2. Click Login"
    
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    mock_open.side_effect = FileNotFoundError 
    
    result = await analyst_node(mock_state)
    
    assert result["status"] == ProcessingStatus.GENERATING
    assert "1. Open Page" in result["test_plan"][0]
    assert result["test_type"] == TestType.UI

@pytest.mark.asyncio
@patch("src.app.agents.nodes.llm")
async def test_coder_node(mock_llm, mock_state):
    """Test Coder node logic."""
    mock_state["test_plan"] = ["1. Do this"]
    
    mock_response = MagicMock()
    mock_response.content = "```python\nprint('code')\n```"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    result = await coder_node(mock_state)
    
    assert result["status"] == ProcessingStatus.VALIDATING
    assert result["generated_code"] == "print('code')"
    assert result["attempts"] == 1

@pytest.mark.asyncio
@patch("src.app.agents.nodes.CodeValidator.validate")
@patch("src.app.agents.nodes.dedup_service")
async def test_reviewer_node_success(mock_dedup, mock_validate, mock_state):
    """Test Reviewer node success path."""
    mock_state["generated_code"] = "valid code"
    mock_validate.return_value = (True, "Success")
    
    result = await reviewer_node(mock_state)
    
    assert result["status"] == ProcessingStatus.COMPLETED
    mock_dedup.save.assert_called_once()

@pytest.mark.asyncio
@patch("src.app.agents.nodes.CodeValidator.validate")
async def test_reviewer_node_failure(mock_validate, mock_state):
    """Test Reviewer node failure path."""
    mock_state["generated_code"] = "invalid code"
    mock_validate.return_value = (False, "Syntax Error")
    
    result = await reviewer_node(mock_state)
    
    assert result["status"] == ProcessingStatus.FIXING
    assert result["validation_error"] == "Syntax Error"
