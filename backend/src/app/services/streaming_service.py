import asyncio
import json
import logging
from collections.abc import AsyncGenerator
import inspect
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import StateSnapshot

from src.app.api.models import ChatMessageRequest, ApprovalRequest
from src.app.domain.enums import ProcessingStatus
from src.app.services.history import HistoryService

logger = logging.getLogger(__name__)


def _state_next_contains(state_obj: StateSnapshot, node_name: str) -> bool:
	"""Best-effort check for pending nodes in LangGraph StateSnapshot."""
	next_val = getattr(state_obj, "next", None)
	if not next_val:
		return False
	try:
		return node_name in list(next_val)
	except Exception:
		return False


async def _maybe_await(value):
	if inspect.isawaitable(value):
		return await value
	return value


class StreamingService:
	def __init__(self, agent_graph: Any, history_service: HistoryService, app_state: Any):
		self.agent_graph = agent_graph
		self.history_service = history_service
		self.app_state = app_state

	async def stream_graph_events(
		self, request_body: ChatMessageRequest, session_id: str
	) -> AsyncGenerator[str, None]:
		"""Handles the main chat flow, starting or continuing a run."""
		# 1. Initialize or Load Run
		if request_body.run_id:
			run = await self.history_service.get_by_id(request_body.run_id, session_id)
			if not run:
				yield f"data: {json.dumps({'type': 'error', 'content': 'Chat session not found'})}\n\n"
				return
			run_id = run.id
			logger.info(f"Continuing chat run {run_id}")
		else:
			run = await self.history_service.create_run(request_body.message, session_id)
			run_id = run.id
			logger.info(f"Created new chat run {run_id}")
			# Send the new Run ID to frontend immediately
			yield f"data: {json.dumps({'type': 'meta', 'run_id': run_id})}\n\n"

		# 2. Prepare LangGraph Config (Persistence)
		config = {"configurable": {"thread_id": str(run_id)}}

		# 3. Update State with User Message
		# Prepare the input, starting with the new message
		input_data = {"messages": [HumanMessage(content=request_body.message)]}

		# If this is a new run, initialize the full state
		if not request_body.run_id:
			input_data.update({
				"run_id": run_id,
				"user_request": request_body.message,
				"model_name": request_body.model_name or "Qwen/Qwen2.5-Coder-32B-Instruct",
				"status": ProcessingStatus.ANALYZING,
				"attempts": 0,
				"validation_error": None,
				"test_plan": [],
				"generated_code": "",
				"test_type": None,
				"logs": [],
			})

		final_code = ""
		final_plan_str = ""
		sent_messages = set()
		final_status: str | None = None

		try:
			# 4. Stream Graph Execution
			async for output in self.agent_graph.astream(input_data, config=config):
				for _node_name, state_update in output.items():
					if not state_update:
						continue

					# Handle Logs
					if "logs" in state_update:
						for log_msg in state_update["logs"]:
							data = json.dumps({"type": "log", "content": log_msg})
							yield f"data: {data}\n\n"

					# Handle Clarification Messages
					if "messages" in state_update:
						last_message = state_update["messages"][-1]
						if isinstance(last_message, AIMessage) and not last_message.tool_calls and last_message.id not in sent_messages:
							data = json.dumps({"type": "message", "content": last_message.content})
							yield f"data: {data}\n\n"
							sent_messages.add(last_message.id)

					# Handle Plan Updates
					if "test_plan" in state_update and state_update["test_plan"]:
						plan_str = "\n".join(state_update["test_plan"])
						final_plan_str = plan_str
						data = json.dumps({"type": "plan", "content": plan_str})
						yield f"data: {data}\n\n"

					# Handle Code Updates
					if "generated_code" in state_update and state_update["generated_code"]:
						final_code = state_update["generated_code"]
						data = json.dumps({"type": "code", "content": final_code})
						yield f"data: {data}\n\n"

					# Handle Status
					if "status" in state_update:
						final_status = state_update["status"]
						data = json.dumps({"type": "status", "content": state_update["status"]})
						yield f"data: {data}\n\n"

					await asyncio.sleep(0.05)

			# 5. If the graph interrupted (HITL), explicitly mark run as waiting and don't force COMPLETED.
			state_snapshot = await _maybe_await(
				self.agent_graph.aget_state(config) if hasattr(self.agent_graph, "aget_state") else self.agent_graph.get_state(config)
			)
			is_waiting_approval = _state_next_contains(state_snapshot, "human_approval")
			if is_waiting_approval:
				# Ensure UI receives an unambiguous status.
				data = json.dumps({"type": "status", "content": ProcessingStatus.WAITING_FOR_APPROVAL})
				yield f"data: {data}\n\n"
				await self.history_service.update_run(
					run_id=run_id,
					status=ProcessingStatus.WAITING_FOR_APPROVAL,
					test_plan=final_plan_str if final_plan_str else None,
				)
				# Finish the stream (frontend should now show the approval UI).
				yield f"data: {json.dumps({'type': 'finish', 'content': 'waiting_for_approval'})}\n\n"
				return

			# 6. Finish (normal completion)
			yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"

			# 7. Save Snapshot (Code only for now, full history is in LangGraph checkpoint)
			# Persist code + plan for History UI (full conversation lives in LangGraph checkpoint).
			if final_code or final_plan_str:
				await self.history_service.update_run(
					run_id=run_id,
					code=final_code if final_code else None,
					status=final_status or ProcessingStatus.COMPLETED,
					test_plan=final_plan_str if final_plan_str else None,
				)

		except Exception as e:
			logger.error(f"Chat Error: {e}", exc_info=True)
			yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
			await self.history_service.update_run(run_id=run_id, status=ProcessingStatus.FAILED)

	async def resume_stream_events(
		self, request_body: ApprovalRequest
	) -> AsyncGenerator[str, None]:
		"""Handles resuming a run after human approval."""
		config = {"configurable": {"thread_id": str(request_body.run_id)}}

		# Optional: update the plan before resuming.
		if request_body.feedback and request_body.feedback.strip():
			new_plan_list = [request_body.feedback.strip()]
			# Update the persisted History row for refresh/reload UX.
			await self.history_service.update_run(run_id=request_body.run_id, status=ProcessingStatus.GENERATING, test_plan=request_body.feedback.strip())
			# Update LangGraph checkpointed state.
			update_payload = {"test_plan": new_plan_list}
			if hasattr(self.agent_graph, "aupdate_state"):
				await _maybe_await(self.agent_graph.aupdate_state(config, update_payload))
			elif hasattr(self.agent_graph, "update_state"):
				await _maybe_await(self.agent_graph.update_state(config, update_payload))

		final_code = ""
		final_plan_str = ""
		final_status: str | None = None
		sent_messages = set()

		# Kick the UI back into processing immediately.
		yield f"data: {json.dumps({'type': 'status', 'content': ProcessingStatus.GENERATING})}\n\n"

		try:
			# By passing None instead of {}, we signal to LangGraph that we want to
			# resume the execution from the last checkpoint without providing new input.
			async for output in self.agent_graph.astream(None, config=config):
				for _node_name, state_update in output.items():
					if not state_update:
						continue

					if "logs" in state_update:
						for log_msg in state_update["logs"]:
							data = json.dumps({"type": "log", "content": log_msg})
							yield f"data: {data}\n\n"

					if "messages" in state_update:
						last_message = state_update["messages"][-1]
						if isinstance(last_message, AIMessage) and not last_message.tool_calls and last_message.id not in sent_messages:
							data = json.dumps({"type": "message", "content": last_message.content})
							yield f"data: {data}\n\n"
							sent_messages.add(last_message.id)

					if "test_plan" in state_update and state_update["test_plan"]:
						plan_str = "\n".join(state_update["test_plan"])
						final_plan_str = plan_str
						data = json.dumps({"type": "plan", "content": plan_str})
						yield f"data: {data}\n\n"

					if "generated_code" in state_update and state_update["generated_code"]:
						final_code = state_update["generated_code"]
						data = json.dumps({"type": "code", "content": final_code})
						yield f"data: {data}\n\n"

					if "status" in state_update:
						final_status = state_update["status"]
						data = json.dumps({"type": "status", "content": final_status})
						yield f"data: {data}\n\n"

					await asyncio.sleep(0.05)

			yield f"data: {json.dumps({'type': 'finish', 'content': 'done'})}\n\n"

			# Persist snapshot for History UI.
			await self.history_service.update_run(
				run_id=request_body.run_id,
				code=final_code if final_code else None,
				status=final_status or ProcessingStatus.COMPLETED,
				test_plan=final_plan_str if final_plan_str else None,
			)
		except Exception as e:
			logger.error(f"Approve/Resume Error: {e}", exc_info=True)
			yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
			await self.history_service.update_run(run_id=request_body.run_id, status=ProcessingStatus.FAILED)

