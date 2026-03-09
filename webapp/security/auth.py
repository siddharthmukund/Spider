"""Authentication and authorization module for Spider SEO Crawler.

Provides API key-based authentication with secure validation.
"""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

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
    Verify API key for protected endpoints.
    
    Uses constant-time comparison to prevent timing attacks.
    
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
    
    try:
        expected_key = get_api_key()
    except RuntimeError as e:
        # Server misconfiguration - API key not set
        raise HTTPException(
            status_code=503,
            detail="API authentication not configured"
        )
    
    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.
    
    Returns:
        str: URL-safe random token (32 bytes = 43 chars base64)
    """
    return secrets.token_urlsafe(32)


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
