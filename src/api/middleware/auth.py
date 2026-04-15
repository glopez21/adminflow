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

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel
import hashlib
import secrets
import jwt

# Get logger for this module
logger = logging.getLogger(__name__)


# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
# These should be moved to environment variables in production

# Secret key for JWT token signing
# IMPORTANT: Change this in production! Use environment variable:
# os.environ.get("API_SECRET_KEY", "change-this-in-production")
SECRET_KEY = "change-this-in-production-use-env-variable"

# Algorithm used for JWT signing
# HS256 is HMAC-SHA256, widely supported and secure
ALGORITHM = "HS256"

# Token expiration time in minutes
# After this time, clients must obtain a new token
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================
# Pre-configured API keys for different access levels
# In production, store these securely (database, secrets manager)
#
# Access Levels:
# - admin: Full read/write access to all endpoints
# - automation: Automated scripts and CI/CD pipelines
# - readonly: Monitoring and read-only operations

API_KEYS = {
    "admin": "ad-admin-key-001",  # Full access - change in production!
    "automation": "ad-auto-key-002",  # Automation access
    "readonly": "ad-read-key-003",  # Read-only access
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================
# Data models for request/response validation


class TokenData(BaseModel):
    """
    JWT token payload data.

    Attributes:
        username: The authenticated username
        scopes: List of permission scopes (e.g., ["read", "write", "admin"])
    """

    username: str
    scopes: list[str] = []


class User(BaseModel):
    """
    User model for authentication.

    Attributes:
        username: Unique username identifier
        password: User's password (plaintext for demo - use hashing in production)
        scopes: Permission scopes granted to this user
    """

    username: str
    password: str
    scopes: list[str] = ["read"]


# ============================================================================
# USER DATABASE (MOCK)
# ============================================================================
# This is a mock database for demonstration purposes.
# In production, replace with actual database lookup.
#
# Default credentials: admin/admin123
# WARNING: Change these in production!

USERS_DB = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "scopes": ["read", "write", "admin"],
    },
    "service": {
        "username": "service",
        "password": "service123",
        "scopes": ["read", "write"],
    },
    "viewer": {"username": "viewer", "password": "viewer123", "scopes": ["read"]},
}


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    In this demo implementation, plain comparison is used.
    In production, use proper password hashing (bcrypt, argon2).

    Args:
        plain_password: The plain text password to verify
        hashed_password: The stored hash to compare against

    Returns:
        bool: True if password matches, False otherwise
    """
    # In production, use: bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    return plain_password == hashed_password


def get_password_hash(password: str) -> str:
    """
    Generate hash of a password for storage.

    Note: SHA-256 is NOT suitable for password hashing!
    Use bcrypt, scrypt, or argon2 in production.

    Args:
        password: Plain text password to hash

    Returns:
        str: Hexadecimal hash string
    """
    # In production, use: bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================================
# USER AUTHENTICATION
# ============================================================================


def authenticate_user(username: str, password: str) -> Optional[User]:
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
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
        expire = datetime.utcnow() + expires_delta
    else:
        # Use default expiration from config
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

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
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Invalid token: missing subject"
            )

        # Return TokenData with username and scopes
        return TokenData(username=username, scopes=payload.get("scopes", []))

    except jwt.ExpiredSignatureError:
        # Token has expired
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        # Other JWT errors (invalid signature, malformed token)
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ============================================================================
# API KEY DEPENDENCIES
# ============================================================================

# Define FastAPI security schemes for dependency injection
# These are used to extract API keys from requests

# API key from X-API-Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# API key from api_key query parameter
api_key_query = APIKeyQuery(name="api_key", auto=False)


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================


async def get_current_user(
    token: str = Depends(lambda: None),
    api_key: Optional[str] = Depends(api_key_header),
    query_key: Optional[str] = Depends(api_key_query),
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
    if token:
        # Token will be verified and converted by other dependencies
        return verify_token(token)

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
