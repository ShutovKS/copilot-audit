import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.api.endpoints.chat import ChatMessageRequest, chat_event_generator


class _AsyncCtx:
	def __init__(self, obj):
		self._obj = obj

	async def __aenter__(self):
		return self._obj

	async def __aexit__(self, exc_type, exc, tb):
		return False


@pytest.mark.asyncio
async def test_chat_persists_test_plan_snapshot() -> None:
	"""Regression: chat endpoint used to persist only code, dropping test_plan in history."""
	fake_db = object()

	# Simulate LangGraph streaming updates.
	async def fake_astream(_input, config=None):
		assert config is not None
		yield {"analyst": {"test_plan": ["Step 1", "Step 2"]}}
		yield {"coder": {"generated_code": "print('ok')"}}
		# End of stream
		return

	fake_graph = SimpleNamespace(astream=fake_astream)
	fake_app_state = SimpleNamespace(agent_graph=fake_graph)

	history_service_mock = MagicMock()
	history_service_mock.get_by_id = AsyncMock(return_value=None)
	history_service_mock.create_run = AsyncMock(return_value=SimpleNamespace(id=123))
	history_service_mock.update_run = AsyncMock(return_value=None)

	with patch("src.app.api.endpoints.chat.AsyncSessionLocal", new=lambda: _AsyncCtx(fake_db)):
		with patch("src.app.api.endpoints.chat.HistoryService", new=lambda db: history_service_mock):
			req = ChatMessageRequest(message="Hello", model_name=None, run_id=None)
			events = []
			async for chunk in chat_event_generator(req, session_id="sess", app_state=fake_app_state):
				events.append(chunk)

	# Ensure a plan event was produced
	assert any("\"type\": \"plan\"" in e for e in events)
	# Ensure DB snapshot includes test_plan
	history_service_mock.update_run.assert_awaited()
	kwargs = history_service_mock.update_run.call_args.kwargs
	assert kwargs.get("run_id") == 123
	assert kwargs.get("test_plan") == "Step 1\nStep 2"
	assert kwargs.get("code") == "print('ok')"

	# Ensure meta event contains run_id
	meta = None
	for e in events:
		if e.startswith("data: "):
			payload = e.replace("data: ", "").strip()
			if payload.endswith("\n\n"):
				payload = payload[:-2]
			try:
				obj = json.loads(payload)
			except Exception:
				continue
			if obj.get("type") == "meta":
				meta = obj
				break
	assert meta is not None and meta.get("run_id") == 123
