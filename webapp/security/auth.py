"""Authentication and authorization module for Spider SEO Crawler.

Provides API key-based authentication with secure validation.
"""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
import os
import datetime

# password hashing helper using bcrypt directly (avoids passlib
# backend detection issues on some platforms like Python 3.14). We keep
# the bcrypt package as a dependency but no longer rely on `passlib`.
import bcrypt

# oauth2 bearer
# Allow the OAuth2 bearer token dependency to be optional (auto_error=False)
# so we can gracefully fall back to API key authentication when no bearer
# token is provided.  The `get_current_user` helper handles both paths.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)

# API key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str:
    """
    Retrieve API key from environment.
    
    Returns:
        str: The API key from WEBAPP_API_KEY environment variable
        
    Raises:
        RuntimeError: If WEBAPP_API_KEY is not set
    """
    key = os.getenv("WEBAPP_API_KEY")
    if not key:
        raise RuntimeError(
            "WEBAPP_API_KEY environment variable must be set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    return key


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify API key for protected endpoints. In the multi-tenant world we
    dispatch to the user store and compare against stored hashed keys.

    ``api_key`` may be either a raw key or a JWT; JWTs are handled by
    `get_current_user` instead.  This dependency remains useful for
    backwards compatibility and service accounts.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # first, try simple environment fallback for quick scripts
    try:
        expected_key = get_api_key()
    except RuntimeError:
        expected_key = None

    if expected_key and secrets.compare_digest(api_key, expected_key):
        return api_key

    # look up in user store
    from webapp.store import load_users
    users = load_users()
    for username, record in users.items():
        for stored_hash in record.get("api_keys", []):
            # stored_hash is hex or bcrypt; use compare_digest to avoid timing
            if secrets.compare_digest(api_key, stored_hash):
                return api_key
    # no match
    raise HTTPException(status_code=403, detail="Invalid API key")


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.
    
    Returns:
        str: URL-safe random token (32 bytes = 43 chars base64)
    """
    return secrets.token_urlsafe(32)


# ---------- multi-tenant helpers ----------
JWT_SECRET = os.getenv("JWT_SECRET", "please-set-a-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against a bcrypt hash.

    Args:
        plain_password: password provided by user
        hashed_password: stored bcrypt hash (utf-8 string)

    Returns:
        bool: True if match, False otherwise.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # If the hash is malformed, treat as non-match
        return False


def get_password_hash(password: str) -> str:
    """Create a bcrypt hash for the given password.

    Returns a utf-8 decoded string so it can be stored in JSON.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION_SECONDS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(API_KEY_HEADER)
):
    # Prefer OAuth2 bearer token when provided
    if token:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        from webapp.store import get_user
        user = get_user(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.get("is_active", True):
            raise HTTPException(status_code=400, detail="Inactive user")
        return user

    # no bearer token, fall back to API key path
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    # verify value (will raise HTTPException on failure)
    validated_key = await verify_api_key(api_key=api_key)

    # attempt to resolve user by api key
    from webapp.store import load_users
    users = load_users()
    for uname, rec in users.items():
        for stored in rec.get('api_keys', []):
            if secrets.compare_digest(validated_key, stored):
                return rec

    # if still not found but env fallback exists, treat as admin
    try:
        expected = get_api_key()
    except RuntimeError:
        expected = None
    if expected and secrets.compare_digest(validated_key, expected):
        return {'username': 'admin', 'scopes': ['*'], 'is_active': True, 'is_superuser': True}

    raise HTTPException(status_code=401, detail="Invalid API key")

    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    from webapp.store import get_user
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

async def authenticate_user(username: str, password: str):
    from webapp.store import get_user
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


# Optional: Support for multiple API keys (for team access)
def verify_api_key_multi(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify API key against multiple allowed keys.
    
    Reads comma-separated keys from WEBAPP_API_KEYS environment variable.
    Fallback to single WEBAPP_API_KEY for backward compatibility.
    
    Args:
        api_key: The API key from request header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: 401 if key missing, 403 if invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Try multi-key mode first
    multi_keys = os.getenv("WEBAPP_API_KEYS", "")
    if multi_keys:
        allowed_keys = [k.strip() for k in multi_keys.split(",") if k.strip()]
        for allowed_key in allowed_keys:
            if secrets.compare_digest(api_key, allowed_key):
                return api_key
    
    # Fallback to single key
    try:
        expected_key = get_api_key()
        if secrets.compare_digest(api_key, expected_key):
            return api_key
    except RuntimeError:
        pass
    
    raise HTTPException(
        status_code=403,
        detail="Invalid API key"
    )
