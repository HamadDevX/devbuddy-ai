from pathlib import Path
from typing import Optional
from config import settings
from supabase import Client
import uuid

class StorageService:
    def __init__(self, db_client: Client):
        self.client = db_client
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    
    async def upload_chat_image(self, user_id: str, image_data: bytes, filename: str) -> Optional[str]:
        """Upload image to Supabase storage"""
        try:
            if len(image_data) > self.max_image_size:
                raise ValueError("Image too large")
            
            file_ext = Path(filename).suffix
            unique_name = f"{uuid.uuid4()}{file_ext}"
            path = f"{user_id}/{unique_name}"
            
            response = self.client.storage.from_("chat-images").upload(
                path,
                image_data
            )
            
            public_url = self.client.storage.from_("chat-images").get_public_url(path)
            return public_url
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    async def upload_payment_screenshot(self, user_id: str, image_data: bytes, filename: str) -> Optional[str]:
        """Upload payment screenshot"""
        try:
            if len(image_data) > self.max_image_size:
                raise ValueError("Image too large")
            
            file_ext = Path(filename).suffix
            unique_name = f"{uuid.uuid4()}{file_ext}"
            path = f"{user_id}/{unique_name}"
            
            response = self.client.storage.from_("payment-screenshots").upload(
                path,
                image_data
            )
            
            public_url = self.client.storage.from_("payment-screenshots").get_public_url(path)
            return public_url
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def validate_image(self, content_type: str) -> bool:
        return content_type in self.allowed_types

storage_service = StorageService