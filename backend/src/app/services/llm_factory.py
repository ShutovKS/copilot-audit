from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.app.core.config import get_settings


class CloudRuLLMService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def get_model(self, model_name: Optional[str] = None) -> BaseChatModel:
        target_model = model_name or self._settings.MODEL_NAME
        
        return ChatOpenAI(
            base_url=self._settings.CLOUD_RU_BASE_URL,
            api_key=self._settings.CLOUD_RU_API_KEY.get_secret_value(),
            model=target_model,
            temperature=0.1,
            max_retries=3,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def check_connection(self) -> str:
        llm = self.get_model()
        message = HumanMessage(content="Hello, are you ready for testing?")
        response = await llm.ainvoke([message])
        return str(response.content)
