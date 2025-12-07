import pytest

from src.app.services.llm_factory import CloudRuLLMService


@pytest.mark.asyncio
async def test_llm_connection() -> None:
    service = CloudRuLLMService()
    response = await service.check_connection()
    
    assert response is not None
    assert len(response) > 0
    print(f"\nLLM Response: {response}")
