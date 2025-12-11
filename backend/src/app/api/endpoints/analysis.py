import os
import shutil
import tempfile
import zipfile
from typing import Annotated  # Added import for Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.app.services.code_analysis.service import CodeAnalysisService

router = APIRouter()


class AnalysisResponse(BaseModel):
	summary: str
	endpoint_count: int


class GitAnalysisRequest(BaseModel):
	url: str
	token: str | None = None


@router.post("/analyze-source", response_model=AnalysisResponse)
async def analyze_source_code(file: Annotated[UploadFile, File(...)]):
	"""
	Accepts a ZIP file with source code (Python/Java/JS/TS).
	Returns a textual summary of API endpoints found.
	"""
	if not file.filename.endswith(".zip"):
		raise HTTPException(status_code=400, detail="Only .zip files are supported")

	service = CodeAnalysisService()

	with tempfile.TemporaryDirectory() as temp_dir:
		zip_path = os.path.join(temp_dir, "source.zip")
		with open(zip_path, "wb") as buffer:
			shutil.copyfileobj(file.file, buffer)

		try:
			with zipfile.ZipFile(zip_path, 'r') as zip_ref:
				zip_ref.extractall(temp_dir)
		except zipfile.BadZipFile:
			raise HTTPException(status_code=400, detail="Invalid zip file") from None

		endpoints = service.analyze_project(temp_dir)
		summary = service.format_for_llm(endpoints)

		return AnalysisResponse(
			summary=summary,
			endpoint_count=len(endpoints)
		)


@router.post("/analyze-git", response_model=AnalysisResponse)
async def analyze_git_repo(request: GitAnalysisRequest):
	"""
	Clones a Git repository (public or private) and analyzes it.
	"""
	service = CodeAnalysisService()
	try:
		endpoints = service.clone_and_analyze(request.url, request.token)
		summary = service.format_for_llm(endpoints)

		return AnalysisResponse(
			summary=summary,
			endpoint_count=len(endpoints)
		)
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e)) from e
