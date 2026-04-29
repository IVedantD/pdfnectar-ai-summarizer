from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import supabase
import logging

logger = logging.getLogger("pdfnectar.auth")
auth_scheme = HTTPBearer(auto_error=True)

async def get_current_user(token: HTTPAuthorizationCredentials = Security(auth_scheme)):
    """Verifies the Supabase JWT token and returns user info."""
    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token.credentials)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_response.user
    except Exception as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            detail = "Token expired"
        elif "invalid" in error_str:
            detail = "Invalid token"
        else:
            detail = "Authentication failed"
            
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
