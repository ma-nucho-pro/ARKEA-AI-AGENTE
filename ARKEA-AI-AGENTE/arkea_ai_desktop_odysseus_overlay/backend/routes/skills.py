from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from backend.arkea_core.skills import create_skill_from_prompt, list_skills, install_markdown_skill, load_skill, install_gemma_default_skill

router = APIRouter(prefix="/api/arkea/skills", tags=["skills"])

class SkillPrompt(BaseModel):
    prompt: str

class SkillMarkdown(BaseModel):
    name: str
    markdown: str

@router.get("")
def get_skills():
    return {"skills": list_skills()}

@router.post("/create")
def create(body: SkillPrompt):
    return create_skill_from_prompt(body.prompt)

@router.post("/install-md")
def install_md(body: SkillMarkdown):
    return install_markdown_skill(body.name, body.markdown)

@router.get("/{skill_id}")
def get_skill(skill_id: str):
    return load_skill(skill_id) or {"error": "skill not found"}


@router.post("/upload-md")
async def upload_md(file: UploadFile = File(...), name: str = Form("")):
    raw = await file.read()
    text = raw.decode("utf-8", errors="replace")
    base_name = name or (file.filename or "skill.md").rsplit('.', 1)[0]
    return install_markdown_skill(base_name, text)


@router.post('/install-gemma')
def install_gemma():
    return install_gemma_default_skill()
