"""
Authentication security utilities
"""
import hashlib
import secrets
from datetime import datetime, timedelta

class AuthSecurity:
    @staticmethod
    def generate_salt():
        """Generate a random salt"""
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac('sha256', 
                                  password.encode('utf-8'), 
                                  salt.encode('utf-8'), 
                                  100000).hex()
    
    @staticmethod
    def verify_password(password: str, salt: str, hashed: str) -> bool:
        """Verify password against hash"""
        return AuthSecurity.hash_password(password, salt) == hashed
    
    @staticmethod
    def generate_farmer_id():
        """Generate unique farmer ID"""
        timestamp = str(int(datetime.now().timestamp()))
        random_part = secrets.token_hex(8)
        return f"farmer_{timestamp}_{random_part}"
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        # Only allow alphanumeric and underscores
        return username.replace('_', '').replace('-', '').isalnum()
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input"""
        if not input_str:
            return ""
        # Remove potentially dangerous characters
        sanitized = input_str.strip()
        # Limit length
        return sanitized[:1000]