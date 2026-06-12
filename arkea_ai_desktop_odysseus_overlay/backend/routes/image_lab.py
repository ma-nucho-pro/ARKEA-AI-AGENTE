from fastapi import APIRouter
from pydantic import BaseModel
from backend.arkea_core.image_lab import generate_placeholder_image, edit_region_placeholder

router = APIRouter(prefix="/api/arkea/image", tags=["image-lab"])

class ImageGenIn(BaseModel):
    prompt: str
    project_id: int | None = None

class ImageEditIn(BaseModel):
    original_path: str
    mask_path: str = ""
    prompt: str
    project_id: int | None = None

@router.post("/generate")
def generate(body: ImageGenIn):
    return generate_placeholder_image(body.prompt, body.project_id)

@router.post("/edit-region")
def edit_region(body: ImageEditIn):
    return edit_region_placeholder(body.original_path, body.mask_path, body.prompt, body.project_id)
