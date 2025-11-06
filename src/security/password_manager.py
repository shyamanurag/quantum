"""
Password Manager - Production-grade password hashing and verification
Uses bcrypt with cost factor 12 for institutional security
"""

import logging
from typing import Optional
import bcrypt

logger = logging.getLogger(__name__)


class PasswordManager:
    """
    Production-grade password manager using bcrypt
    Cost factor 12 provides strong security while maintaining performance
    """
    
    # Cost factor 12 = ~250ms per hash on modern CPU
    # Provides excellent security against brute force attacks
    BCRYPT_COST_FACTOR = 12
    
    @classmethod
    def hash_password(cls, plain_password: str) -> str:
        """
        Hash a plain password using bcrypt
        
        Args:
            plain_password: The plain text password
            
        Returns:
            Hashed password as string (includes salt)
            
        Raises:
            ValueError: If password is empty or too long
        """
        if not plain_password:
            raise ValueError("Password cannot be empty")
        
        if len(plain_password) > 72:
            raise ValueError("Password cannot exceed 72 characters (bcrypt limitation)")
        
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt(rounds=cls.BCRYPT_COST_FACTOR)
            hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password
        
        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to check against
            
        Returns:
            True if password matches, False otherwise
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    @classmethod
    def needs_rehash(cls, hashed_password: str) -> bool:
        """
        Check if a hashed password needs to be rehashed
        (e.g., if cost factor has changed)
        
        Args:
            hashed_password: The hashed password to check
            
        Returns:
            True if password should be rehashed
        """
        try:
            # Extract cost factor from hash
            # bcrypt hash format: $2b$12$... where 12 is the cost factor
            parts = hashed_password.split('$')
            if len(parts) >= 3:
                current_cost = int(parts[2])
                return current_cost < cls.BCRYPT_COST_FACTOR
            return False
        except Exception:
            # If we can't determine, assume it needs rehashing
            return True

