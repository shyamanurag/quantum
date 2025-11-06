"""
Secure Authentication API endpoints
Production-ready authentication with bcrypt password hashing and rate limiting
NO DEFAULT CREDENTIALS - Production security enforced
"""
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import sys
import os
from pathlib import Path
import uuid

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.password_manager import PasswordManager
from src.security.token_manager import TokenManager

# Models
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)

class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    username: str
    role: str
    expires_at: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)
    email: EmailStr
    role: str = Field(default="user", pattern="^(user|admin)$")

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    created_at: str
    is_active: bool

class LogoutRequest(BaseModel):
    """Logout request model"""
    pass

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Initialize security managers
password_manager = PasswordManager()
token_manager = None  # Will be initialized with Redis client when app starts

# Rate limiting storage (IP -> [attempt_times])
login_attempts: Dict[str, list] = {}
RATE_LIMIT_ATTEMPTS = 10
RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds

# User database - MUST use PostgreSQL in production
# This in-memory store is ONLY for development/testing
users_db: Dict[str, Dict[str, Any]] = {}  # Empty - NO default users


def init_token_manager(redis_client):
    """Initialize token manager with Redis client"""
    global token_manager
    token_manager = TokenManager(redis_client)
    logger.info("Token manager initialized with Redis")


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded IP (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> bool:
    """
    Check if IP has exceeded rate limit
    
    Returns:
        True if under limit, False if exceeded
    """
    now = datetime.utcnow().timestamp()
    
    # Get attempts for this IP
    attempts = login_attempts.get(ip, [])
    
    # Remove old attempts outside the window
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    
    # Update attempts
    login_attempts[ip] = attempts
    
    # Check limit
    return len(attempts) < RATE_LIMIT_ATTEMPTS


def record_login_attempt(ip: str):
    """Record a login attempt for rate limiting"""
    now = datetime.utcnow().timestamp()
    if ip not in login_attempts:
        login_attempts[ip] = []
    login_attempts[ip].append(now)


def get_user(username: str) -> Optional[Dict]:
    """Get user from database"""
    return users_db.get(username)


def create_user_in_db(username: str, email: str, password_hash: str, role: str = "user") -> Dict:
    """
    Create user in database
    
    Args:
        username: Username
        email: User email
        password_hash: Hashed password
        role: User role (user or admin)
        
    Returns:
        Created user dictionary
    """
    user = {
        "user_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    users_db[username] = user
    return user


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user from JWT token"""
    if not token_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    
    # Verify token
    token_data = token_manager.verify_token(credentials.credentials)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = get_user(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


# API Endpoints

@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request):
    """
    User login endpoint with rate limiting
    
    - Rate limit: 10 attempts per 15 minutes per IP
    - Passwords verified using bcrypt
    - Returns JWT access token valid for 24 hours
    """
    try:
        # Check rate limiting
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again in 15 minutes."
            )
        
        # Get user
        user = get_user(login_request.username)
        if not user:
            record_login_attempt(client_ip)
            logger.warning(f"Login attempt for non-existent user: {login_request.username} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not password_manager.verify_password(login_request.password, user["password_hash"]):
            record_login_attempt(client_ip)
            logger.warning(f"Failed login attempt for user {login_request.username} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Check if token manager is initialized
        if not token_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not initialized"
            )
        
        # Create access token
        access_token, expires_at = token_manager.create_access_token(
            user_id=user["user_id"],
            username=user["username"],
            role=user["role"]
        )
        
        logger.info(f"User {login_request.username} logged in successfully from {client_ip}")
        
        return LoginResponse(
            access_token=access_token,
            user_id=user["user_id"],
            username=user["username"],
            role=user["role"],
            expires_at=expires_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout endpoint - revokes the current access token
    """
    try:
        if not token_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not initialized"
            )
        
        # Revoke the token
        success = token_manager.revoke_token(credentials.credentials)
        
        if success:
            logger.info("User logged out successfully")
            return {"message": "Successfully logged out"}
        else:
            return {"message": "Logout processed (token revocation unavailable)"}
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate, current_user: Dict = Depends(get_current_user)):
    """
    Register a new user (admin only)
    
    - Requires admin authentication
    - Passwords hashed with bcrypt (cost factor 12)
    - Minimum password length: 8 characters
    """
    try:
        # Check if current user is admin
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create users"
            )
        
        # Check if username already exists
        if get_user(user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash password
        password_hash = password_manager.hash_password(user_create.password)
        
        # Create user
        user = create_user_in_db(
            username=user_create.username,
            email=user_create.email,
            password_hash=password_hash,
            role=user_create.role
        )
        
        logger.info(f"New user created: {user_create.username} by {current_user['username']}")
        
        return UserResponse(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return UserResponse(
        user_id=current_user["user_id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"],
        is_active=current_user["is_active"]
    )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Change password for current user
    """
    try:
        # Verify old password
        if not password_manager.verify_password(old_password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )
        
        # Validate new password
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters"
            )
        
        # Hash new password
        new_password_hash = password_manager.hash_password(new_password)
        
        # Update user (in real DB, this would be an UPDATE query)
        users_db[current_user["username"]]["password_hash"] = new_password_hash
        
        logger.info(f"Password changed for user {current_user['username']}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
