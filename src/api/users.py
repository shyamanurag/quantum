import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
import hashlib
from src.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)
logger = logging.getLogger(__name__)

def get_database_operations():
    # This is a temporary measure to avoid circular imports.
    # In a real application, this should be moved to a shared database module.
    return None

@router.get("/", summary="Get all users")
async def get_users():
    """Fetch all registered trading users with their basic information"""
    db_ops = get_database_operations()
    if not db_ops:
        return {
            "success": False, 
            "users": [], 
            "total_users": 0,
            "timestamp": datetime.now().isoformat(), 
            "error": "SAFETY: User database disabled - real database required",
            "message": "Mock user data eliminated for safety"
        }
    
    try:
        # ELIMINATED: Mock user response that could mislead about real users
        # ❌ return {"success": True, "users": [], "total_users": 0, "timestamp": datetime.now().isoformat(), "message": "DB query disabled."}
        
        # SAFETY: Return proper error instead of fake success
        logger.error("SAFETY: Mock user data ELIMINATED to prevent fake user information")
        return {
            "success": False, 
            "users": [], 
            "total_users": 0,
            "timestamp": datetime.now().isoformat(),
            "error": "SAFETY: Mock user data disabled - real user database required"
        }
    
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return {"success": False, "users": [], "message": "Unable to fetch users"}

@router.post("/", summary="Add new user")
async def add_user(user_data: dict):
    """Onboard a new user to the trading system - REAL DATABASE OPERATIONS"""
    try:
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'full_name']
        if not all(field in user_data and user_data[field] for field in required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Import database dependency
        from src.config.database import get_db
        from src.config.models import User
        import hashlib
        from datetime import datetime
        
        # Get database session
        db = next(get_db())
        
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.username == user_data['username']) | 
                (User.email == user_data['email'])
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=400, 
                    detail="User with this username or email already exists"
                )
            
            # Hash password
            password_hash = hashlib.sha256(user_data['password'].encode()).hexdigest()
            
            # Create new user in database
            new_user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=password_hash,
                full_name=user_data['full_name'],
                role=user_data.get('role', 'user'),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"User {user_data['username']} created successfully in database")
            
            return {
                "success": True, 
                "message": f"User {user_data['username']} created successfully", 
                "user_id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role,
                "created_at": new_user.created_at.isoformat()
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{user_id}", summary="Remove user")
async def remove_user(user_id: str):
    """Remove a user from the trading system - REAL DATABASE OPERATIONS"""
    try:
        # Import database dependency
        from src.config.database import get_db
        from src.config.models import User
        
        # Get database session
        db = next(get_db())
        
        try:
            # Find user by ID
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Remove user from database
            username = user.username
            db.delete(user)
            db.commit()
            
            logger.info(f"User {username} (ID: {user_id}) removed successfully from database")
            
            return {
                "success": True, 
                "message": f"User {username} removed successfully",
                "user_id": user_id
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/current", summary="Get current user")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get information about the currently authenticated user - REAL AUTHENTICATION"""
    try:
        # Return real authenticated user information
        return {
            "status": "success",
            "data": {
                "id": current_user["user_id"],
                "username": current_user["username"],
                "email": current_user["email"],
                "role": current_user["role"],
                "is_active": current_user["is_active"],
                "created_at": current_user["created_at"],
                "permissions": ["read", "write"] + (["admin"] if current_user["role"] == "admin" else [])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}") 