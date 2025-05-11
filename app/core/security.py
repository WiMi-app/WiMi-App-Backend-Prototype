from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt for secure storage.
    
    Args:
        password (str): Plain text password to hash
        
    Returns:
        str: Securely hashed password
    """
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain (str): Plain text password
        hashed (str): Hashed password to compare against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str) -> str:
    """
    Create a JWT access token with expiration.
    
    Args:
        subject (str): Subject of the token, typically user ID
        
    Returns:
        str: Encoded JWT token
    """
    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": subject}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT access token.
    
    Args:
        token (str): JWT token to decode
        
    Returns:
        str: Subject from token (typically user ID)
        
    Raises:
        Exception: Various JWT exceptions if token is invalid
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    return payload.get("sub")
