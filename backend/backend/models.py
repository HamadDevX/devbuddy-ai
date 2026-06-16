from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileResponse(BaseModel):
    id: str
    username: Optional[str]
    email: str
    tier: str
    theme_preference: str
    daily_message_count: int
    daily_photo_count: int
    daily_download_count: int
    premium_expires_at: Optional[str]
    created_at: str

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tech_stack: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    tech_stack: Optional[str]
    description: Optional[str]
    created_at: str

class ChatMessage(BaseModel):
    role: str
    content: str
    explain_mode: Optional[str] = None
    humanizer_mode: Optional[str] = None
    code_language: Optional[str] = None
    has_image: bool = False
    image_urls: Optional[List[str]] = None

class ChatCreate(BaseModel):
    project_id: Optional[str]
    messages: List[ChatMessage]
    mode: str = "chat"

class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    mode: str
    explain_mode: Optional[str]
    humanizer_mode: Optional[str]
    created_at: str

class PaymentCreate(BaseModel):
    plan: str = "monthly"
    transaction_id: Optional[str]
    screenshot_url: Optional[str]
    amount: int

class PaymentResponse(BaseModel):
    id: str
    amount: int
    plan: str
    status: str
    transaction_id: Optional[str]
    created_at: str

class ThemeUpdate(BaseModel):
    theme: str = Field(..., pattern="^(light|dark|coder)$")

class CodeExecutionRequest(BaseModel):
    code: str
    language: str

class CodeExecutionResponse(BaseModel):
    output: str
    language: str
    success: bool