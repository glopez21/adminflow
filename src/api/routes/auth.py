"""Authentication API endpoints for AdminFlow.

Provides JWT token acquisition via username/password login.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.api.middleware.auth import (
    authenticate_user,
    create_access_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Obtain a JWT access token.

    Authenticates with username and password, returns a signed JWT
    token for subsequent API requests.

    Args:
        form_data: OAuth2 form with username and password fields.

    Returns:
        dict: access_token, token_type, and expiration info.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=timedelta(minutes=60),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }
