from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.arkea_core.research import research_query, scihub_blocked

router = APIRouter(prefix="/api/arkea/research", tags=["research"])

class ResearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=10, ge=1, le=50)

@router.post("/search")
def search(body: ResearchIn):
    return research_query(body.query, body.limit)

@router.get("/scihub")
def scihub():
    return scihub_blocked()
