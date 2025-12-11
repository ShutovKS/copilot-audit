from datetime import datetime
from typing import Annotated  # Added import for Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.services.history import HistoryService

router = APIRouter()


class TestRunSchema(BaseModel):
	id: int
	user_request: str
	test_type: str | None
	status: str
	generated_code: str | None
	test_plan: str | None
	created_at: datetime

	class Config:
		from_attributes = True


class ChatMessageSchema(BaseModel):
	type: str
	content: str


class TestRunDetailsSchema(TestRunSchema):
	messages: list[ChatMessageSchema] = []


@router.get("/", response_model=list[TestRunSchema])
async def get_history(
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	service = HistoryService(db)
	return await service.get_all(x_session_id)


@router.get("/{run_id}", response_model=TestRunDetailsSchema)
async def get_run(
		run_id: int,
		request: Request,
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	# Pass the connection pool from the app state to the service
	connection_pool = request.app.state.connection_pool
	service = HistoryService(db, connection_pool)

	run_details = await service.get_run_details(run_id, x_session_id)
	if not run_details:
		raise HTTPException(status_code=404, detail="Run not found or access denied")

	# Convert BaseMessage objects to a serializable format
	messages_serializable = []
	for msg in run_details.get("messages", []):
		if isinstance(msg, (HumanMessage, AIMessage)):
			messages_serializable.append({"type": msg.type, "content": msg.content})

	run_data = run_details['run'].__dict__
	run_data['messages'] = messages_serializable

	return TestRunDetailsSchema(**run_data)
