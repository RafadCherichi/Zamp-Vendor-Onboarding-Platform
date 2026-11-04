import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import bcrypt
import jwt
from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Securely hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def generate_invitation_token() -> Tuple[str, str]:
    """
    Generate a high-entropy, cryptographically random token for vendor invitations.
    Returns:
        (raw_token, token_hash)
        Only token_hash must be stored in the database.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_invitation_token(raw_token)
    return raw_token, token_hash


def hash_invitation_token(raw_token: str) -> str:
    """Compute the SHA-256 hash of a raw invitation token for database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
