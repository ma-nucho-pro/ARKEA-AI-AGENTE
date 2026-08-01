from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from backend.arkea_core.skills import create_skill_from_prompt, list_skills, install_markdown_skill, load_skill, install_gemma_default_skill
from backend.arkea_core.security import read_upload_limited
from backend.arkea_core.db import execute, get_setting, upsert_setting

router = APIRouter(prefix="/api/arkea/skills", tags=["skills"])

class SkillPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)

class SkillMarkdown(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    markdown: str = Field(min_length=1, max_length=2_000_000)


class SkillActivation(BaseModel):
    skill_id: str = Field(default="", max_length=100)

@router.get("")
def get_skills():
    return {"skills": list_skills(), "active_skill_id": get_setting("active_skill_id", "")}

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
    try:
        raw = await read_upload_limited(file, 2 * 1024 * 1024)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    text = raw.decode("utf-8", errors="replace")
    base_name = name or (file.filename or "skill.md").rsplit('.', 1)[0]
    return install_markdown_skill(base_name, text)


@router.post('/install-gemma')
def install_gemma():
    return install_gemma_default_skill()


@router.post("/activate")
def activate_skill(body: SkillActivation):
    if body.skill_id:
        skill = load_skill(body.skill_id)
        if not skill or not skill.get("enabled"):
            raise HTTPException(404, "Skill activa no encontrada")
    upsert_setting("active_skill_id", body.skill_id)
    return {"ok": True, "active_skill_id": body.skill_id}


@router.post("/{skill_id}/toggle")
def toggle_skill(skill_id: str):
    skill = load_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill no encontrada")
    enabled = 0 if skill.get("enabled") else 1
    execute("UPDATE skills SET enabled=? WHERE skill_id=?", (enabled, skill_id))
    if not enabled and get_setting("active_skill_id", "") == skill_id:
        upsert_setting("active_skill_id", "")
    return {"ok": True, "enabled": bool(enabled)}
