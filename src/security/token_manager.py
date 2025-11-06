"""
Token Manager - Production-grade JWT token management with revocation
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import jwt
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Token data structure"""
    user_id: str
    username: str
    role: str
    expires_at: datetime


class TokenManager:
    """
    Production-grade JWT token manager with Redis-based revocation
    """
    
    # Token expiration times
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    
    # JWT algorithm
    ALGORITHM = "HS256"
    
    def __init__(self, redis_client=None):
        """
        Initialize token manager
        
        Args:
            redis_client: Redis client for token blacklist (optional)
        """
        self.redis_client = redis_client
        
        # Get JWT secret from environment
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise RuntimeError(
                "JWT_SECRET_KEY environment variable is required. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        
        if len(self.secret_key) < 64:
            logger.warning(
                f"JWT_SECRET_KEY is only {len(self.secret_key)} characters. "
                "Recommended minimum is 64 characters for production security."
            )
    
    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, datetime]:
        """
        Create a new access token
        
        Args:
            user_id: User identifier
            username: Username
            role: User role
            expires_delta: Optional custom expiration delta
            
        Returns:
            Tuple of (token string, expiration datetime)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.ACCESS_TOKEN_EXPIRE_HOURS)
        
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.ALGORITHM)
            logger.info(f"Created access token for user {username} (expires: {expire})")
            return encoded_jwt, expire
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise
    
    def create_refresh_token(
        self,
        user_id: str,
        username: str
    ) -> tuple[str, datetime]:
        """
        Create a new refresh token
        
        Args:
            user_id: User identifier
            username: Username
            
        Returns:
            Tuple of (token string, expiration datetime)
        """
        expire = datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.ALGORITHM)
            logger.info(f"Created refresh token for user {username}")
            return encoded_jwt, expire
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData if valid, None if invalid or expired
        """
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                logger.warning("Attempted to use blacklisted token")
                return None
            
            # Decode and verify token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
            
            # Extract data
            token_data = TokenData(
                user_id=payload.get("user_id"),
                username=payload.get("sub"),
                role=payload.get("role", "user"),
                expires_at=datetime.fromtimestamp(payload.get("exp"))
            )
            
            return token_data
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token by adding it to the blacklist
        
        Args:
            token: JWT token to revoke
            
        Returns:
            True if successfully revoked
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot revoke token")
            return False
        
        try:
            # Decode to get expiration (without verification)
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            exp = payload.get("exp")
            
            if not exp:
                return False
            
            # Calculate TTL (time until expiration)
            ttl = int(exp - datetime.utcnow().timestamp())
            
            if ttl > 0:
                # Add to blacklist with TTL
                key = f"blacklist:{token}"
                self.redis_client.setex(key, ttl, "1")
                logger.info("Token revoked and added to blacklist")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted
        
        Args:
            token: JWT token to check
            
        Returns:
            True if blacklisted
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"blacklist:{token}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            # Fail secure - if we can't check, assume it's blacklisted
            return True
    
    def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        Revoke all tokens for a specific user
        (useful for logout from all devices)
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot revoke user tokens")
            return False
        
        try:
            # Set a flag that this user's tokens are invalid
            key = f"user_revoked:{user_id}"
            # Keep for 30 days (max token lifetime)
            self.redis_client.setex(key, 30 * 24 * 60 * 60, "1")
            logger.info(f"All tokens revoked for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke user tokens: {e}")
            return False

