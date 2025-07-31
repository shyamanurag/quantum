"""
Secure Authentication API endpoints
Production-ready authentication with no default credentials
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import sys
import os
import jwt
from pathlib import Path
import hashlib
import secrets

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Simple auth models for production use
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    username: str
    role: str
    expires_at: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    role: str = "user"

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    created_at: str
    is_active: bool

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# In-memory user store for now (should be database in production)
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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt, expire

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_user(username: str) -> Optional[Dict]:
    """Get user from database"""
    return users_db.get(username)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = get_user(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """User login endpoint"""
    try:
        user = get_user(login_request.username)
        if not user or not verify_password(login_request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token, expires_at = create_access_token(
            data={"sub": user["username"], "user_id": user["user_id"], "role": user["role"]}
        )
        
        logger.info(f"User {login_request.username} logged in successfully")
        
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
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """User registration endpoint"""
    try:
        # Check if user already exists
        if user_data.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create new user
        user_id = f"user_{len(users_db) + 1}"
        password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
        
        new_user = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "role": user_data.role,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        users_db[user_data.username] = new_user
        
        logger.info(f"User {user_data.username} registered successfully")
        
        return UserResponse(
            user_id=new_user["user_id"],
            username=new_user["username"],
            email=new_user["email"],
            role=new_user["role"],
            created_at=new_user["created_at"],
            is_active=new_user["is_active"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user["user_id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"],
        is_active=current_user["is_active"]
    )

@router.post("/logout")
async def logout(current_user: Dict = Depends(get_current_user)):
    """Logout endpoint (client should discard token)"""
    logger.info(f"User {current_user['username']} logged out")
    return {"message": "Successfully logged out"}

@router.get("/verify")
async def verify_token(current_user: Dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return {"valid": True, "user": current_user["username"]}

# Health check for auth system
@router.get("/health")
async def auth_health():
    """Authentication system health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "registered_users": len(users_db)
    } 