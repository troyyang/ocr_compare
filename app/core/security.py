# core/security.py
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from core.config import SECRET_KEY
from core.error_handle import AuthorizationException

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with auto-generated salt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token with expiration"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or 
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decode and validate JWT access token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.DecodeError as e:
        raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg="Invalid token") from e
    except jwt.ExpiredSignatureError as e:
        raise AuthorizationException(code=AuthorizationException.EXPIRED_TOKEN, msg="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg="Invalid token") from e
    except jwt.PyJWTError as e:
        raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg="Invalid token") from e

# Generate test passwords (run once and store hashes)
if __name__ == "__main__":
    # WARNING: These should NOT be used in production
    print("# TEST PASSWORDS (for development only)")
    print(f"admin_hash = '{hash_password('Admin123!')}'")      # Password: Admin123!
    print(f"user_hash = '{hash_password('TestUser@2023')}'")   # Password: TestUser@2023
    print(f"api_hash = '{hash_password('SecureAPI#456')}'")    # Password: SecureAPI#456