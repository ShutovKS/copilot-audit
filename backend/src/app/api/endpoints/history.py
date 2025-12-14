from datetime import datetime
from typing import Annotated  # Added import for Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.services.history import HistoryService
from src.app.services.storage import storage_service # Added import

router = APIRouter()


class TestRunSchema(BaseModel):
	id: int
	user_request: str
	test_type: str | None
	status: str
	generated_code_content: str | None = None # Changed to content
	test_plan_content: str | None = None      # Changed to content
	execution_logs_content: str | None = None  # Added content field
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
	runs = await service.get_all(x_session_id)
	
	response_runs = []
	for run in runs:
		generated_code_content = None
		if run.generated_code_path:
			generated_code_content = storage_service.load(run.generated_code_path)
		
		test_plan_content = None
		if run.test_plan_path:
			test_plan_content = storage_service.load(run.test_plan_path)

		execution_logs_content = None
		if run.execution_logs_path:
			execution_logs_content = storage_service.load(run.execution_logs_path)

		response_runs.append(TestRunSchema(
			id=run.id,
			user_request=run.user_request,
			test_type=run.test_type,
			status=run.status,
			generated_code_content=generated_code_content,
			test_plan_content=test_plan_content,
			execution_logs_content=execution_logs_content,
			created_at=run.created_at
		))
	return response_runs


@router.get("/{run_id}", response_model=TestRunDetailsSchema)
async def get_run(
		run_id: int,
		request: Request,
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID")
):
	# Pass the connection pool from the app state to the service
	connection_pool = request.app.state.connection_pool
	service = HistoryService(db)

	run_details = await service.get_run_details(run_id, x_session_id, connection_pool)
	if not run_details:
		raise HTTPException(status_code=404, detail="Run not found or access denied")

	# Convert BaseMessage objects to a serializable format
	messages_serializable = []
	for msg in run_details.get("messages", []):
		if isinstance(msg, (HumanMessage, AIMessage)):
			messages_serializable.append({"type": msg.type, "content": msg.content})

	run = run_details['run']
	
	generated_code_content = None
	if run.generated_code_path:
		generated_code_content = storage_service.load(run.generated_code_path)
	
	test_plan_content = None
	if run.test_plan_path:
		test_plan_content = storage_service.load(run.test_plan_path)

	execution_logs_content = None
	if run.execution_logs_path:
		execution_logs_content = storage_service.load(run.execution_logs_path)

	# Fallback: if DB snapshot doesn't have plan/code, take them from LangGraph checkpoint.
	if not test_plan_content and run_details.get("checkpoint_test_plan"):
		test_plan_content = run_details["checkpoint_test_plan"]
	if not generated_code_content and run_details.get("checkpoint_generated_code"):
		generated_code_content = run_details["checkpoint_generated_code"]
	
	return TestRunDetailsSchema(
		id=run.id,
		user_request=run.user_request,
		test_type=run.test_type,
		status=run.status,
		generated_code_content=generated_code_content,
		test_plan_content=test_plan_content,
		execution_logs_content=execution_logs_content,
		created_at=run.created_at,
		messages=messages_serializable
	)
