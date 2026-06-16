from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from config import settings
import httpx
from typing import Dict, Any

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token from Supabase"""
    token = credentials.credentials
    
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.SUPABASE_ANON_KEY
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )

async def get_current_user(user: Dict[str, Any] = Depends(verify_token)) -> str:
    """Get current user ID"""
    return user.get("id")