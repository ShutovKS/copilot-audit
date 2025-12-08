from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.app.services.gitlab import GitLabService

router = APIRouter()

class GitLabExportRequest(BaseModel):
    code: str
    project_id: str = Field(..., description="GitLab Project ID (e.g. 123456)")
    token: str = Field(..., description="Personal Access Token with api scope")
    url: str = Field("https://gitlab.com", description="GitLab Instance URL")
    title: str = "Automated Test Case"

class GitLabExportResponse(BaseModel):
    status: str
    mr_url: str
    branch: str

@router.post("/gitlab", response_model=GitLabExportResponse)
async def export_to_gitlab(request: GitLabExportRequest):
    """
    Exports the generated test to a real GitLab repository via Merge Request.
    """
    try:
        # Determine base API URL
        api_url = f"{request.url.rstrip('/')}/api/v4"
        
        service = GitLabService(token=request.token, base_url=api_url)
        result = await service.create_mr(
            project_id=request.project_id,
            code=request.code,
            title=request.title
        )
        return GitLabExportResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
