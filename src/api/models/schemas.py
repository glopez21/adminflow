"""
Pydantic Models for AdminFlow API.

This module defines all request/response schemas for the AdminFlow REST API.
These models provide input validation and serialization for various endpoints.

Models:
    UserCreate: Schema for creating new AD user accounts
    UserUpdate: Schema for updating existing user attributes
    UserResponse: Schema for user account information responses
    GroupCreate: Schema for creating AD groups
    GroupMemberAdd: Schema for adding/removing group members
    SystemCreate: Schema for adding systems to inventory
    SystemUpdate: Schema for updating system information
    RemoteConnectionRequest: Schema for remote connection testing
    NetworkScanRequest: Schema for network scanning operations
    HealthCheckRequest: Schema for target health checks

Usage:
    from src.api.models.schemas import UserCreate, SystemCreate

    user = UserCreate(
        username="jsmith",
        first_name="John",
        last_name="Smith",
        email="jsmith@domain.com",
        password="SecurePass123",
        department="IT",
        title="Systems Administrator"
    )
"""

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """
    Schema for creating a new Active Directory user account.

    Attributes:
        username: The user's sAMAccountName (logon name)
        first_name: User's given name
        last_name: User's surname
        email: User's email address (validated as proper email format)
        password: Initial password for the account
        ou: Target Organizational Unit DN (optional, uses default if not specified)
        department: User's department attribute
        title: User's job title
        enabled: Whether the account should be enabled on creation (default: True)

    Example:
        user = UserCreate(
            username="jsmith",
            first_name="John",
            last_name="Smith",
            email="jsmith@company.com",
            password="SecurePass123!",
            department="Engineering",
            title="Software Engineer"
        )
    """

    username: str
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    ou: str | None = None
    department: str | None = None
    title: str | None = None
    enabled: bool = True


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    title: str | None = None


class UserResponse(BaseModel):
    username: str
    email: str | None = None
    display_name: str | None = None
    department: str | None = None
    title: str | None = None
    enabled: bool
    created: str | None = None
    last_logon: str | None = None


class GroupCreate(BaseModel):
    name: str
    group_scope: str = "Global"
    group_type: str = "Security"
    ou: str | None = None


class GroupMemberAdd(BaseModel):
    group_name: str
    member_dn: str


class SystemCreate(BaseModel):
    hostname: str
    ip_address: str
    system_type: str
    os: str | None = None
    description: str | None = None
    location: str | None = None
    tags: list[str] | None = None


class SystemUpdate(BaseModel):
    hostname: str | None = None
    ip_address: str | None = None
    os: str | None = None
    description: str | None = None
    location: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class RemoteConnectionRequest(BaseModel):
    target_host: str
    connection_type: str
    port: int | None = None
    credentials: dict | None = None
    timeout: int = 30


class NetworkScanRequest(BaseModel):
    network_range: str
    scan_types: list[str]
    ports: list[int] | None = None


class HealthCheckRequest(BaseModel):
    target: str
    check_type: str
    port: int | None = None
    timeout: int = 10
