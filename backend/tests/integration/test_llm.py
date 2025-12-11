from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.services.llm_factory import CloudRuLLMService


@pytest.mark.asyncio
@patch("src.app.services.llm_factory.ChatOpenAI")
async def test_llm_connection(mock_chat_openai) -> None:
    # Setup Mock
    mock_llm_instance = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "I am ready!"
    mock_llm_instance.ainvoke.return_value = mock_response

    mock_chat_openai.return_value = mock_llm_instance

    service = CloudRuLLMService()
    # We mock the internal llm property or the class initialization
    # Since we patched ChatOpenAI class, service._llm will be our mock instance

    response = await service.check_connection()

    assert response == "I am ready!"
    assert len(response) > 0
