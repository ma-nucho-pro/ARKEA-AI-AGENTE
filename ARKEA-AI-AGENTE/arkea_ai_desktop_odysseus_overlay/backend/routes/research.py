from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.research import research_query, scihub_blocked

router = APIRouter(prefix="/api/arkea/research", tags=["research"])

class ResearchIn(BaseModel):
    query: str
    limit: int = 10

@router.post("/search")
def search(body: ResearchIn):
    return research_query(body.query, body.limit)

@router.get("/scihub")
def scihub():
    return scihub_blocked()
