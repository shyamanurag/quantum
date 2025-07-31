#!/usr/bin/env python3
"""
Generate secure keys for Digital Ocean production deployment
Run this script to generate secure JWT, encryption, and secret keys
"""

import secrets
import string
import hashlib

def generate_secure_key(length=32):
    """Generate a secure random key of specified length"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=32):
    """Generate a secure hex key"""
    return secrets.token_hex(length)

def generate_jwt_secret():
    """Generate JWT secret (minimum 32 characters)"""
    return generate_secure_key(64)

def generate_encryption_key():
    """Generate encryption key (exactly 32 bytes for AES-256)"""
    return generate_hex_key(16)  # 16 bytes = 32 hex chars

def generate_session_secret():
    """Generate session secret key"""
    return generate_secure_key(48)

def generate_webhook_secret():
    """Generate webhook secret"""
    return generate_secure_key(40)

if __name__ == "__main__":
    print("🔐 GENERATING SECURE KEYS FOR DIGITAL OCEAN DEPLOYMENT")
    print("=" * 60)
    
    print("\n📋 COPY THESE VALUES TO YOUR DIGITAL OCEAN ENV VARIABLES:")
    print("-" * 60)
    
    # Generate all keys
    jwt_secret = generate_jwt_secret()
    encryption_key = generate_encryption_key()
    session_secret = generate_session_secret()
    webhook_secret = generate_webhook_secret()
    
    # Print in DO format
    print(f"JWT_SECRET={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print(f"SECRET_KEY={session_secret}")
    print(f"WEBHOOK_SECRET={webhook_secret}")
    
    print("\n" + "=" * 60)
    print("✅ SECURE KEYS GENERATED SUCCESSFULLY!")
    print("⚠️  IMPORTANT: Save these keys securely and use them in production only!")
    print("⚠️  DO NOT commit these keys to version control!")
    print("=" * 60)
    
    # Validate key lengths
    print(f"\n🔍 KEY VALIDATION:")
    print(f"JWT Secret length: {len(jwt_secret)} characters (✅ >= 32)")
    print(f"Encryption key length: {len(encryption_key)} characters (✅ = 32)")
    print(f"Session secret length: {len(session_secret)} characters (✅ >= 32)")
    print(f"Webhook secret length: {len(webhook_secret)} characters (✅ >= 32)")