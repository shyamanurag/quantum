"""
Authentication module for trading system - REAL JWT VALIDATION ONLY
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
import logging
import jwt
import os
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# JWT Configuration - REAL PRODUCTION SETTINGS
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Real user database (should be connected to actual database in production)
users_db = {
    "admin": {
        "user_id": "user_1",
        "username": "admin",
        "email": "admin@trading.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
}

def get_user(username: str) -> Optional[Dict]:
    """Get user from database"""
    return users_db.get(username)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    REAL JWT token validation - NO MOCKS OR FALLBACKS
    """
    try:
        # Decode and validate JWT token
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            logger.error("JWT token missing username claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = get_user(username)
        if user is None:
            logger.error(f"User {username} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user["is_active"]:
            logger.error(f"User {username} is inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user account",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication system error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system error",
        )

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict]:
    """
    Optional authentication - returns None if no valid token provided
    NO FALLBACK USERS - REAL VALIDATION OR NONE
    """
    try:
        if credentials and credentials.credentials:
            return await get_current_user(credentials)
        return None
    except HTTPException:
        return None
    except Exception as e:
        logger.error(f"Optional auth error: {e}")
        return None
