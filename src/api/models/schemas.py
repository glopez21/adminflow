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

from typing import List, Optional

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
    ou: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    enabled: bool = True


class UserUpdate(BaseModel):
    """
    Schema for updating existing user account attributes.

    All fields are optional - only provided fields will be updated.

    Attributes:
        first_name: User's given name
        last_name: User's surname
        email: User's email address
        department: User's department
        title: User's job title
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    title: Optional[str] = None


class UserResponse(BaseModel):
    """
    Schema for user account information in API responses.

    Attributes:
        username: User's sAMAccountName
        email: User's email address
        display_name: User's display name
        department: User's department
        title: User's job title
        enabled: Whether the account is enabled
        created: Account creation timestamp
        last_logon: Last logon timestamp
    """

    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    enabled: bool
    created: Optional[str] = None
    last_logon: Optional[str] = None


class GroupCreate(BaseModel):
    """
    Schema for creating a new Active Directory group.

    Attributes:
        name: Group's common name (CN)
        group_scope: Group scope (Global, Universal, DomainLocal)
        group_type: Group type (Security, Distribution)
        ou: Target Organizational Unit DN (optional)
    """

    name: str
    group_scope: str = "Global"
    group_type: str = "Security"
    ou: Optional[str] = None


class GroupMemberAdd(BaseModel):
    """
    Schema for adding or removing a member from a group.

    Attributes:
        group_name: Name of the target group
        member_dn: Distinguished Name of the member to add/remove

    Example:
        member = GroupMemberAdd(
            group_name="IT-Administrators",
            member_dn="CN=John Smith,OU=Users,DC=domain,DC=com"
        )
    """

    group_name: str
    member_dn: str


class SystemCreate(BaseModel):
    """
    Schema for adding a system to the inventory.

    Attributes:
        hostname: System's hostname
        ip_address: System's IP address
        system_type: Type of system (windows, linux, macos, network, printer, server, storage, iot)
        os: Operating system name and version
        description: Human-readable description
        physical_location: Physical location of the system
        tags: List of tags for categorization and search
    """

    hostname: str
    ip_address: str
    system_type: str
    os: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None


class SystemUpdate(BaseModel):
    """
    Schema for updating system inventory information.

    All fields are optional - only provided fields will be updated.

    Attributes:
        hostname: Updated hostname
        ip_address: Updated IP address
        os: Updated operating system
        description: Updated description
        location: Updated physical location
        tags: Updated tags list
        status: Updated status (active, inactive, maintenance)
    """

    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    os: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class RemoteConnectionRequest(BaseModel):
    """
    Schema for testing remote connectivity to a system.

    Attributes:
        target_host: Target hostname or IP address
        connection_type: Type of connection (ssh, rdp, vnc, winrm, smb, ping, port)
        port: Optional custom port (uses defaults based on connection_type if not specified)
        credentials: Optional dictionary with username/password
        timeout: Connection timeout in seconds (default: 30)

    Example:
        req = RemoteConnectionRequest(
            target_host="192.168.1.100",
            connection_type="ssh",
            port=22,
            timeout=10
        )
    """

    target_host: str
    connection_type: str
    port: Optional[int] = None
    credentials: Optional[dict] = None
    timeout: int = 30


class NetworkScanRequest(BaseModel):
    """
    Schema for requesting a network scan operation.

    Attributes:
        network_range: CIDR notation for the network to scan (e.g., "192.168.1.0/24")
        scan_types: List of scan types to perform (ping, port, service)
        ports: Optional custom list of ports to scan (defaults to common ports)

    Example:
        req = NetworkScanRequest(
            network_range="10.0.0.0/24",
            scan_types=["ping", "port"],
            ports=[22, 80, 443, 3389]
        )
    """

    network_range: str
    scan_types: List[str]
    ports: Optional[List[int]] = None


class HealthCheckRequest(BaseModel):
    """
    Schema for performing a health check on a specific target.

    Attributes:
        target: Target hostname or IP address
        check_type: Type of check to perform (ping, port, service, url)
        port: Port number for port/service checks (optional for ping/url)
        timeout: Timeout in seconds for the check (default: 10)

    Example:
        req = HealthCheckRequest(
            target="dc01.domain.com",
            check_type="port",
            port=389,
            timeout=5
        )
    """

    target: str
    check_type: str
    port: Optional[int] = None
    timeout: int = 10
