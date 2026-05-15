"""
API Authentication and Authorization Middleware.

This module provides comprehensive authentication and authorization features
for the AdminFlow REST API. It supports multiple authentication methods
including API keys and JWT tokens with role-based access control.

Authentication Methods:
1. API Keys: Pre-configured keys for simple integration
2. JWT Tokens: Time-limited tokens with embedded claims

Authorization:
- Role-based access control (RBAC)
- Scope-based permissions
- Dependency injection for route protection

Security Considerations:
- Default keys MUST be changed in production
- Use strong SECRET_KEY (via environment variable)
- Tokens expire after configured duration
- Implement HTTPS in production

Example:
    # Using API Key in header
    curl -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/users

    # Using JWT token
    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expiration_minutes

API_KEYS = {
    "admin": settings.api_key_ad_admin,
    "automation": settings.api_key_ad_auto,
    "readonly": settings.api_key_ad_read,
}

DEFAULT_API_KEYS = {"ad-admin-key-001", "ad-auto-key-002", "ad-read-key-003"}

if not os.environ.get("ADMINFLOW_SUPPRESS_KEY_WARNING"):
    for name, key in API_KEYS.items():
        if key in DEFAULT_API_KEYS:
            logger.warning(
                "DEFAULT API KEY IN USE for '%s': set %s environment variable "
                "to a unique value in production",
                name,
                f"API_KEY_{name.upper()}",
            )


class TokenData(BaseModel):
    username: str
    scopes: list[str] = []


class User(BaseModel):
    username: str
    password: str
    scopes: list[str] = ["read"]


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


USERS_DB: dict[str, dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password": _hash_password("admin123"),
        "scopes": ["read", "write", "admin"],
    },
    "service": {
        "username": "service",
        "password": _hash_password("service123"),
        "scopes": ["read", "write"],
    },
    "viewer": {
        "username": "viewer",
        "password": _hash_password("viewer123"),
        "scopes": ["read"],
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _hash_password(plain_password) == hashed_password


# ============================================================================
# USER AUTHENTICATION
# ============================================================================


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.

    Looks up the user in the database and verifies credentials.
    Returns User object if authentication succeeds, None otherwise.

    Args:
        username: The username to authenticate
        password: The password to verify

    Returns:
        Optional[User]: User object if authenticated, None if failed
    """
    # Look up user in database
    user = USERS_DB.get(username)

    # User not found
    if not user:
        logger.debug(f"Authentication failed: user '{username}' not found")
        return None

    # Verify password
    if not verify_password(password, user["password"]):
        logger.debug(f"Authentication failed: invalid password for '{username}'")
        return None

    # Authentication successful - return User object
    return User(
        username=user["username"], password=user["password"], scopes=user["scopes"]
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with embedded user data.

    The token contains:
    - sub (subject): Username
    - exp (expiration): Token expiry time
    - scopes: User's permission scopes

    Args:
        data: Dictionary with token payload data
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token string
    """
    # Create copy to avoid modifying original data
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        # Use custom expiration if provided
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use default expiration from config
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add expiration claim to payload
    to_encode.update({"exp": expire})

    # Encode and return JWT token
    # Uses HS256 algorithm with SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.

    Validates:
    1. Token signature (using SECRET_KEY)
    2. Token expiration
    3. Required claims

    Args:
        token: The JWT token string to verify

    Returns:
        TokenData: Decoded token data

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode token with secret key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract username from subject claim
        username = payload.get("sub")
        if username is None or not isinstance(username, str):
            raise HTTPException(
                status_code=401, detail="Invalid token: missing subject"
            )

        # Return TokenData with username and scopes
        return TokenData(username=username, scopes=payload.get("scopes", []))

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired") from None
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e


# ============================================================================
# API KEY DEPENDENCIES
# ============================================================================

# Define FastAPI security schemes for dependency injection
# These are used to extract API keys from requests

# API key from X-API-Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# API key from api_key query parameter
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
    query_key: str | None = Depends(api_key_query),
):
    """
    FastAPI dependency for authentication.

    This function checks for authentication credentials in the following order:
    1. API Key in X-API-Key header
    2. API Key in api_key query parameter
    3. JWT Token in Authorization header (via Depends)

    Returns TokenData with user info and scopes if authenticated.
    Raises 401 if no valid credentials provided.

    This is used as a dependency in route handlers:
        @router.get("/users")
        async def list_users(current_user: TokenData = Depends(get_current_user)):
            ...

    Args:
        token: JWT token from Authorization header (injected by other dependency)
        api_key: API key from X-API-Key header
        query_key: API key from query parameter

    Returns:
        TokenData: Authenticated user's data and permissions

    Raises:
        HTTPException: 401 if no valid credentials, 403 if invalid API key
    """
    # -----------------------------------------------------------------------
    # Method 1: Check X-API-Key header
    # -----------------------------------------------------------------------
    if api_key:
        # Search through known API keys
        for username, key in API_KEYS.items():
            if key == api_key:
                logger.debug(f"Authenticated via header API key: {username}")
                return TokenData(username=username, scopes=["read", "write"])

        # Key not found in known keys
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API key")

    # -----------------------------------------------------------------------
    # Method 2: Check api_key query parameter
    # -----------------------------------------------------------------------
    if query_key:
        # Search through known API keys
        for username, key in API_KEYS.items():
            if key == query_key:
                logger.debug(f"Authenticated via query API key: {username}")
                return TokenData(username=username, scopes=["read", "write"])

        # Key not found
        logger.warning(f"Invalid query API key attempted: {query_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API key")

    # -----------------------------------------------------------------------
    # Method 3: Check JWT token (from Authorization header)
    # -----------------------------------------------------------------------
    if credentials is not None:
        return verify_token(credentials.credentials)

    # -----------------------------------------------------------------------
    # No credentials provided
    # -----------------------------------------------------------------------
    raise HTTPException(
        status_code=401,
        detail="No authentication credentials provided. "
        "Provide either API key (X-API-Key header or api_key param) "
        "or JWT token (Authorization header)",
    )


# ============================================================================
# AUTHORIZATION DEPENDENCIES
# ============================================================================


async def get_admin_user(current_user: TokenData = Depends(get_current_user)):
    """
    Dependency to require admin privileges.

    Use this for routes that require admin-level access:
        @router.post("/admin/...")
        async def admin_operation(admin: TokenData = Depends(get_admin_user)):
            ...

    Args:
        current_user: The authenticated user from get_current_user

    Returns:
        TokenData: The current user if admin

    Raises:
        HTTPException: 403 if user doesn't have admin scope
    """
    # Check if admin scope is present
    if "admin" not in current_user.scopes:
        logger.warning(
            f"User '{current_user.username}' attempted admin operation without permission"
        )
        raise HTTPException(
            status_code=403, detail="Admin privileges required for this operation"
        )

    return current_user


def require_scope(scope: str):
    """
    Factory function to create scope-based authorization dependency.

    Use this to require specific scopes for endpoints:
        @router.get("/sensitive")
        async def sensitive_data(
            user: TokenData = Depends(require_scope("admin"))
        ):
            ...

    Args:
        scope: The required scope (e.g., "read", "write", "admin")

    Returns:
        A FastAPI dependency function
    """

    async def scope_checker(current_user: TokenData = Depends(get_current_user)):
        """
        Inner function that performs the actual scope check.

        Checks if the user has either:
        1. The specific required scope
        2. Admin scope (which implies all other scopes)

        Args:
            current_user: The authenticated user

        Returns:
            TokenData: The current user if authorized

        Raises:
            HTTPException: 403 if scope requirement not met
        """
        # Check if user has the required scope OR is admin
        if scope not in current_user.scopes and "admin" not in current_user.scopes:
            logger.warning(
                f"User '{current_user.username}' lacks required scope: {scope}"
            )
            raise HTTPException(
                status_code=403, detail=f"Scope '{scope}' required for this operation"
            )

        return current_user

    return scope_checker
