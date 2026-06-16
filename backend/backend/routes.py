from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from auth import get_current_user
from database import db
from ai_service import ai_service
from storage_service import StorageService
from models import (
    ProfileResponse, ProjectCreate, ProjectResponse, ChatCreate,
    PaymentCreate, PaymentResponse, ThemeUpdate, CodeExecutionRequest, CodeExecutionResponse
)
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# ===== PROFILE ROUTES =====
@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user_id: str = Depends(get_current_user)):
    profile = await db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/profile/theme", response_model=ProfileResponse)
async def update_theme(theme_data: ThemeUpdate, user_id: str = Depends(get_current_user)):
    profile = await db.update_theme(user_id, theme_data.theme)
    return profile

# ===== PROJECT ROUTES =====
@router.post("/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, user_id: str = Depends(get_current_user)):
    profile = await db.get_profile(user_id)
    
    if profile.get("tier") == "free":
        existing = await db.get_projects(user_id)
        if len(existing) >= 1:
            raise HTTPException(status_code=429, detail="Free tier limited to 1 project")
    
    project = await db.create_project(
        user_id,
        project_data.name,
        project_data.tech_stack,
        project_data.description
    )
    return project

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(user_id: str = Depends(get_current_user)):
    projects = await db.get_projects(user_id)
    return projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user_id: str = Depends(get_current_user)):
    project = await db.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user_id: str = Depends(get_current_user)):
    success = await db.delete_project(project_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

# ===== CHAT ROUTES =====
@router.post("/chat")
async def chat(chat_data: ChatCreate, user_id: str = Depends(get_current_user)):
    profile = await db.get_profile(user_id)
    
    # Check message limit
    can_send, remaining = await db.check_limits(user_id, "messages")
    if not can_send:
        raise HTTPException(status_code=429, detail="Daily limit reached. Upgrade to premium for unlimited messages.")
    
    # Validate project
    if chat_data.project_id:
        project = await db.get_project(chat_data.project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Prepare messages for AI
    messages = []
    for msg in chat_data.messages[:-1]:
        messages.append({"role": msg.role, "content": msg.content})
    
    last_msg = chat_data.messages[-1]
    
    # Get AI response
    try:
        ai_response = await ai_service.chat(
            messages=messages + [{"role": "user", "content": last_msg.content}],
            mode=chat_data.mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
    
    # Save user message
    await db.create_chat(
        user_id=user_id,
        project_id=chat_data.project_id,
        role="user",
        content=last_msg.content,
        mode=chat_data.mode
    )
    
    # Save assistant response
    await db.create_chat(
        user_id=user_id,
        project_id=chat_data.project_id,
        role="assistant",
        content=ai_response,
        mode=chat_data.mode
    )
    
    # Increment counter
    await db.increment_counter(user_id, "daily_message_count")
    
    return {
        "response": ai_response,
        "remaining_messages": remaining - 1
    }

@router.get("/chats/{project_id}")
async def get_chats(project_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    chats = await db.get_chats(user_id, project_id)
    return {"chats": chats}

@router.delete("/chats/{project_id}")
async def delete_chats(project_id: str, user_id: str = Depends(get_current_user)):
    await db.delete_chat_history(user_id, project_id)
    return {"success": True}

# ===== CODE EXECUTION =====
@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(req: CodeExecutionRequest, user_id: str = Depends(get_current_user)):
    if not ai_service.validate_code_format(req.code, req.language):
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    output = await ai_service.execute_code(req.code, req.language)
    
    return CodeExecutionResponse(
        output=output,
        language=req.language,
        success=not output.startswith("Error:")
    )

# ===== IMAGE UPLOAD =====
@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    profile = await db.get_profile(user_id)
    
    # Check photo limit
    can_upload, _ = await db.check_limits(user_id, "photos")
    if not can_upload:
        raise HTTPException(status_code=429, detail="Daily photo limit reached")
    
    # Validate file
    if file.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
    
    storage_svc = StorageService(db.client)
    url = await storage_svc.upload_chat_image(user_id, content, file.filename)
    
    if not url:
        raise HTTPException(status_code=500, detail="Upload failed")
    
    await db.increment_counter(user_id, "daily_photo_count")
    
    return {"url": url}

# ===== EXPORT =====
@router.get("/export/{project_id}")
async def export_chat(
    project_id: str,
    format: str = "txt",
    user_id: str = Depends(get_current_user)
):
    profile = await db.get_profile(user_id)
    
    # Check download limit for free tier
    if profile.get("tier") == "free":
        can_download, _ = await db.check_limits(user_id, "downloads")
        if not can_download:
            raise HTTPException(status_code=429, detail="Daily download limit reached")
        
        if format != "txt":
            raise HTTPException(status_code=403, detail="Free tier: .txt format only")
    
    chats = await db.get_chats(user_id, project_id)
    
    content = "\n\n".join([f"[{msg['role'].upper()}]\n{msg['content']}" for msg in chats])
    
    await db.increment_counter(user_id, "daily_download_count")
    
    return StreamingResponse(
        iter([content.encode()]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=export.{format}"}
    )

# ===== PAYMENT ROUTES =====
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    user_id: str = Depends(get_current_user)
):
    payment = await db.create_payment(
        user_id=user_id,
        amount=payment_data.amount,
        plan=payment_data.plan,
        transaction_id=payment_data.transaction_id,
        screenshot_url=payment_data.screenshot_url
    )
    return payment

@router.post("/payments/{payment_id}/screenshot")
async def upload_payment_screenshot(
    payment_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    payment = await db.get_payment(payment_id, user_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    content = await file.read()
    storage_svc = StorageService(db.client)
    url = await storage_svc.upload_payment_screenshot(user_id, content, file.filename)
    
    if not url:
        raise HTTPException(status_code=500, detail="Upload failed")
    
    return {"url": url}

@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(user_id: str = Depends(get_current_user)):
    payments = await db.get_payments(user_id)
    return payments