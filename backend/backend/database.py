from supabase import create_client, Client
from config import settings
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
import pytz

class Database:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        self.admin_client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    
    def get_pkt_date(self) -> date:
        """Get current date in Pakistan timezone"""
        pkt = pytz.timezone('Asia/Karachi')
        return datetime.now(pkt).date()
    
    # PROFILES
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        response = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
        return response.data if response.data else None
    
    async def create_profile(self, user_id: str, email: str, username: str = None) -> Dict[str, Any]:
        profile_data = {
            "id": user_id,
            "email": email,
            "username": username or email.split("@")[0],
            "tier": "free",
            "trial_start_date": datetime.utcnow().isoformat(),
            "theme_preference": "dark"
        }
        response = self.client.table("profiles").insert(profile_data).execute()
        return response.data[0] if response.data else profile_data
    
    async def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("profiles").update(updates).eq("id", user_id).execute()
        return response.data[0] if response.data else {}
    
    async def update_theme(self, user_id: str, theme: str) -> Dict[str, Any]:
        return await self.update_profile(user_id, {"theme_preference": theme})
    
    async def reset_daily_limits(self, user_id: str) -> None:
        """Reset daily counts if date has changed"""
        profile = await self.get_profile(user_id)
        if profile:
            last_reset = datetime.fromisoformat(profile.get("daily_reset_date", "2024-01-01")).date()
            if last_reset < self.get_pkt_date():
                await self.update_profile(user_id, {
                    "daily_message_count": 0,
                    "daily_photo_count": 0,
                    "daily_download_count": 0,
                    "daily_reset_date": self.get_pkt_date().isoformat()
                })
    
    async def check_limits(self, user_id: str, limit_type: str) -> tuple[bool, int]:
        """Check if user has hit daily/plan limits"""
        profile = await self.get_profile(user_id)
        if not profile:
            return False, 0
        
        await self.reset_daily_limits(user_id)
        profile = await self.get_profile(user_id)
        
        if profile.get("tier") == "premium":
            return True, 999999
        
        trial_days = (self.get_pkt_date() - datetime.fromisoformat(profile.get("trial_start_date", datetime.utcnow().isoformat())).date()).days
        
        if limit_type == "messages":
            if trial_days < 7:
                return True, 999999
            limit = 50
            current = profile.get("daily_message_count", 0)
        elif limit_type == "photos":
            limit = 3
            current = profile.get("daily_photo_count", 0)
        elif limit_type == "downloads":
            limit = 2
            current = profile.get("daily_download_count", 0)
        else:
            return False, 0
        
        return current < limit, limit - current
    
    async def increment_counter(self, user_id: str, counter: str) -> None:
        profile = await self.get_profile(user_id)
        if profile:
            current = profile.get(counter, 0)
            await self.update_profile(user_id, {counter: current + 1})
    
    # PROJECTS
    async def create_project(self, user_id: str, name: str, tech_stack: str = None, description: str = None) -> Dict[str, Any]:
        project_data = {
            "user_id": user_id,
            "name": name,
            "tech_stack": tech_stack,
            "description": description
        }
        response = self.client.table("projects").insert(project_data).execute()
        return response.data[0] if response.data else {}
    
    async def get_projects(self, user_id: str) -> List[Dict[str, Any]]:
        profile = await self.get_profile(user_id)
        if profile.get("tier") == "premium":
            response = self.client.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        else:
            response = self.client.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        return response.data if response.data else []
    
    async def get_project(self, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        response = self.client.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).single().execute()
        return response.data if response.data else None
    
    async def delete_project(self, project_id: str, user_id: str) -> bool:
        response = self.client.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute()
        return len(response.data) > 0 if response.data else False
    
    # CHATS
    async def create_chat(self, user_id: str, project_id: str, role: str, content: str, mode: str = "chat", explain_mode: str = None, humanizer_mode: str = None, has_image: bool = False, image_urls: List[str] = None, code_language: str = None) -> Dict[str, Any]:
        chat_data = {
            "user_id": user_id,
            "project_id": project_id,
            "role": role,
            "content": content,
            "mode": mode,
            "explain_mode": explain_mode,
            "humanizer_mode": humanizer_mode,
            "has_image": has_image,
            "image_urls": image_urls or [],
            "code_language": code_language
        }
        response = self.client.table("chats").insert(chat_data).execute()
        return response.data[0] if response.data else {}
    
    async def get_chats(self, user_id: str, project_id: str = None) -> List[Dict[str, Any]]:
        query = self.client.table("chats").select("*").eq("user_id", user_id)
        if project_id:
            query = query.eq("project_id", project_id)
        response = query.order("created_at", desc=False).execute()
        return response.data if response.data else []
    
    async def delete_chat_history(self, user_id: str, project_id: str = None) -> bool:
        query = self.client.table("chats").delete().eq("user_id", user_id)
        if project_id:
            query = query.eq("project_id", project_id)
        response = query.execute()
        return True
    
    # PAYMENTS
    async def create_payment(self, user_id: str, amount: int, plan: str = "monthly", transaction_id: str = None, screenshot_url: str = None) -> Dict[str, Any]:
        payment_data = {
            "user_id": user_id,
            "amount": amount,
            "plan": plan,
            "transaction_id": transaction_id,
            "screenshot_url": screenshot_url,
            "status": "pending"
        }
        response = self.client.table("payments").insert(payment_data).execute()
        return response.data[0] if response.data else {}
    
    async def get_payments(self, user_id: str) -> List[Dict[str, Any]]:
        response = self.client.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data if response.data else []
    
    async def get_payment(self, payment_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        response = self.client.table("payments").select("*").eq("id", payment_id).eq("user_id", user_id).single().execute()
        return response.data if response.data else None
    
    async def verify_payment(self, payment_id: str, admin_notes: str = None) -> Dict[str, Any]:
        response = self.client.table("payments").update({"status": "verified", "admin_notes": admin_notes}).eq("id", payment_id).execute()
        payment = response.data[0] if response.data else {}
        
        if payment:
            expire_date = datetime.utcnow() + timedelta(days=30 if payment.get("plan") == "monthly" else 365)
            await self.update_profile(payment["user_id"], {
                "tier": "premium",
                "premium_expires_at": expire_date.isoformat(),
                "payment_status": "verified",
                "transaction_id": payment.get("transaction_id")
            })
        
        return payment
    
    async def reject_payment(self, payment_id: str, reason: str = None) -> Dict[str, Any]:
        response = self.client.table("payments").update({"status": "rejected", "admin_notes": reason}).eq("id", payment_id).execute()
        return response.data[0] if response.data else {}
    
    async def check_premium_expiry(self, user_id: str) -> None:
        """Downgrade to free if premium expired"""
        profile = await self.get_profile(user_id)
        if profile and profile.get("tier") == "premium":
            expire_date = datetime.fromisoformat(profile.get("premium_expires_at", datetime.utcnow().isoformat()))
            if expire_date < datetime.utcnow():
                await self.update_profile(user_id, {"tier": "free"})

db = Database()