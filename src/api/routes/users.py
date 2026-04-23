"""
User Management API Endpoints for AdminFlow.

This module provides REST API endpoints for managing Active Directory user
accounts. It supports creating users, retrieving user information, enabling/disabling
accounts, password reset, moving users between OUs, and bulk operations.

Endpoints:
    POST /api/users/ - Create a new AD user
    GET /api/users/{username} - Get user account information
    PUT /api/users/{username}/disable - Disable a user account
    PUT /api/users/{username}/enable - Enable a user account
    PUT /api/users/{username}/reset-password - Reset user password
    PUT /api/users/{username}/move - Move user to different OU
    GET /api/users/inactive/{days} - Find inactive users
    POST /api/users/bulk - Create multiple users at once

Authentication:
    Requires API key or JWT token with appropriate scopes.

Example:
    # Create a new user
    curl -X POST -H "X-API-Key: ad-admin-key-001" \
         -H "Content-Type: application/json" \
         -d '{"username": "jsmith", "first_name": "John", \
             "last_name": "Smith", "email": "jsmith@domain.com", \
             "password": "SecurePass123!", "department": "IT"}' \
         http://localhost:8000/api/users/
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

import config.settings as settings
from src.api.models.schemas import UserCreate
from src.user_management.ad_user_manager import ADUserManager
from src.utils.ad_connection import ADConnection

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_manager():
    """
    Create and connect a user manager instance.

    Returns:
        tuple: (ADUserManager instance, AD connection)
    """
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    conn.connect()
    return ADUserManager(conn), conn


@router.post("/", response_model=dict)
async def create_user(user: UserCreate):
    """
    Create a new Active Directory user account.

    Creates a new user in the specified Organizational Unit with the
    provided attributes. The account is created enabled by default.

    Args:
        user: UserCreate schema with user details

    Returns:
        dict: Success status and created user information

    Raises:
        HTTPException: If user creation fails (400) or already exists (404)
    """
    manager, conn = get_user_manager()
    try:
        result = manager.create_user(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            password=user.password,
            ou=user.ou or settings.DEFAULT_OU,
            department=user.department,
            title=user.title,
            enabled=user.enabled,
        )
        return result
    finally:
        conn.disconnect()


@router.get("/{username}", response_model=dict)
async def get_user(username: str):
    """
    Get detailed information about a user account.

    Retrieves comprehensive user account information including
    attributes like email, department, title, enabled status,
    creation date, and last logon timestamp.

    Args:
        username: The sAMAccountName of the user to retrieve

    Returns:
        dict: User account information

    Raises:
        HTTPException: If user not found (404)
    """
    manager, conn = get_user_manager()
    try:
        result = manager.get_user_info(username)
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    finally:
        conn.disconnect()


@router.put("/{username}/disable")
async def disable_user(username: str):
    """
    Disable an Active Directory user account.

    Disables the specified user account. The account remains in AD
    but cannot authenticate. Use this for temporary deactivation
    or as part of offboarding process.

    Args:
        username: The sAMAccountName of the user to disable

    Returns:
        dict: Success status

    Raises:
        HTTPException: If operation fails (400)
    """
    manager, conn = get_user_manager()
    try:
        result = manager.disable_user(username)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    finally:
        conn.disconnect()


@router.put("/{username}/enable")
async def enable_user(username: str):
    """
    Enable a previously disabled Active Directory user account.

    Re-enables a disabled user account, restoring the ability to
    authenticate and access resources.

    Args:
        username: The sAMAccountName of the user to enable

    Returns:
        dict: Success status

    Raises:
        HTTPException: If operation fails (400)
    """
    manager, conn = get_user_manager()
    try:
        result = manager.enable_user(username)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    finally:
        conn.disconnect()


@router.put("/{username}/reset-password")
async def reset_password(username: str, new_password: str):
    """
    Reset a user's password.

    Sets a new password for the specified user account. The user
    will be prompted to change their password on next logon if
    password policy requires it.

    Args:
        username: The sAMAccountName of the user
        new_password: The new password to set

    Returns:
        dict: Success status

    Raises:
        HTTPException: If operation fails (400)
    """
    manager, conn = get_user_manager()
    try:
        result = manager.reset_password(username, new_password)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    finally:
        conn.disconnect()


@router.put("/{username}/move")
async def move_user(username: str, new_ou: str):
    """
    Move a user to a different Organizational Unit.

    Relocates the user account to a different OU while preserving
    all attributes and group memberships. This is useful for
    restructuring or during employee department transfers.

    Args:
        username: The sAMAccountName of the user to move
        new_ou: The Distinguished Name of the target OU

    Returns:
        dict: Success status with new OU location

    Raises:
        HTTPException: If operation fails (400)

    Example:
        new_ou = "OU=Archive,DC=domain,DC=com"
    """
    manager, conn = get_user_manager()
    try:
        result = manager.move_user(username, new_ou)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    finally:
        conn.disconnect()


@router.get("/inactive/{days}")
async def get_inactive_users(days: int = 90):
    """
    Find users who haven't logged in for specified days.

    Queries Active Directory for user accounts that haven't authenticated
    within the specified number of days. These accounts may be candidates
    for disablement or removal as part of security hygiene practices.

    Args:
        days: Number of days of inactivity threshold (default: 90)

    Returns:
        dict: Count and list of inactive users

    Example:
        GET /api/users/inactive/180 - Find users inactive for 6 months

    Response:
        {
            "count": 15,
            "users": [
                {"username": "jdoe", "last_logon": "2024-01-15", "email": "..."},
                ...
            ]
        }
    """
    manager, conn = get_user_manager()
    try:
        result = manager.find_inactive_users(days)
        return {"count": len(result), "users": result}
    finally:
        conn.disconnect()


@router.post("/bulk")
async def bulk_create_users(users: List[UserCreate]):
    """
    Create multiple users in a single operation.

    Bulk creates user accounts from a list of UserCreate schemas.
    Each user is processed sequentially, and partial success is
    possible - some users may succeed while others fail.

    Args:
        users: List of UserCreate schemas

    Returns:
        dict: Results with success and failure counts

    Example:
        POST /api/users/bulk
        [
            {"username": "user1", "first_name": "John", ...},
            {"username": "user2", "first_name": "Jane", ...}
        ]
    """
    manager, conn = get_user_manager()
    try:
        user_list = [u.dict() for u in users]
        result = manager.bulk_create_users(user_list)
        return result
    finally:
        conn.disconnect()
