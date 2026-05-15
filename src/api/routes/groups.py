"""
Group Management API Endpoints for AdminFlow.

This module provides REST API endpoints for managing Active Directory security
and distribution groups. It supports creating groups, managing membership,
querying groups by user, finding empty groups, and bulk operations.

Endpoints:
    POST /api/groups/ - Create a new AD group
    GET /api/groups/{group_name}/members - Get all group members
    POST /api/groups/add-member - Add a member to a group
    POST /api/groups/remove-member - Remove a member from a group
    GET /api/groups/user/{username}/groups - Get user's group memberships
    GET /api/groups/empty - Find groups with no members
    POST /api/groups/bulk-add/{group_name} - Add multiple members

Authentication:
    Requires API key or JWT token with appropriate scopes.

Example:
    # Create a new group
    curl -X POST -H "X-API-Key: ad-admin-key-001" \
         -H "Content-Type: application/json" \
         -d '{"name": "IT-Administrators", "group_scope": "Global", \
             "group_type": "Security"}' \
         http://localhost:8000/api/groups/

    # Get group members
    curl -H "Authorization: Bearer <token>" \
         http://localhost:8000/api/groups/Domain-Admins/members
"""

import logging

from fastapi import APIRouter, Body

import config.settings as settings
from src.api.models.schemas import GroupCreate, GroupMemberAdd
from src.user_management.group_management import ADGroupManager
from src.utils.ad_connection import get_pooled_connection, release_connection

logger = logging.getLogger(__name__)
router = APIRouter()


def get_group_manager():
    """
    Acquire a pooled AD connection and create a group manager.

    Returns:
        tuple: (ADGroupManager instance, AD connection)
    """
    conn = get_pooled_connection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    return ADGroupManager(conn), conn


@router.post("/", response_model=dict)
async def create_group(group: GroupCreate):
    """
    Create a new Active Directory security or distribution group.

    Creates a new group in the specified Organizational Unit with the
    specified scope and type. Security groups are used for access control
    while distribution groups are used for email distribution lists.

    Args:
        group: GroupCreate schema with group details

    Returns:
        dict: Success status and created group information

    Raises:
        HTTPException: If group creation fails (400)
    """
    manager, conn = get_group_manager()
    try:
        result = manager.create_group(
            group_name=group.name,
            group_scope=group.group_scope,
            group_type=group.group_type,
            ou=group.ou,
        )
        return result
    finally:
        release_connection(conn)


@router.get("/{group_name}/members")
async def get_group_members(group_name: str):
    """
    Get all members of a specific group.

    Retrieves all user and group members of the specified AD group.
    Members inherit permissions assigned to the group.

    Args:
        group_name: The name (CN) of the group

    Returns:
        dict: Group name, member list, and count

    Example Response:
        {
            "group": "Domain-Admins",
            "members": ["admin", "jsmith", "mjohnson"],
            "count": 3
        }
    """
    manager, conn = get_group_manager()
    try:
        members = manager.get_group_members(group_name)
        return {"group": group_name, "members": members, "count": len(members)}
    finally:
        release_connection(conn)


@router.post("/add-member")
async def add_group_member(member: GroupMemberAdd):
    """
    Add a member to an existing group.

    Adds a user or another group as a member of the specified group.
    The member is identified by their Distinguished Name (DN).

    Args:
        member: GroupMemberAdd schema with group and member DN

    Returns:
        dict: Success status

    Example:
        POST /api/groups/add-member
        {
            "group_name": "IT-Administrators",
            "member_dn": "CN=John Smith,OU=Users,DC=domain,DC=com"
        }
    """
    manager, conn = get_group_manager()
    try:
        result = manager.add_member(member.group_name, member.member_dn)
        return result
    finally:
        release_connection(conn)


@router.post("/remove-member")
async def remove_group_member(member: GroupMemberAdd):
    """
    Remove a member from a group.

    Removes a user or group from the specified group. The member
    loses all permissions granted by this group's membership.

    Args:
        member: GroupMemberAdd schema with group and member DN

    Returns:
        dict: Success status

    Example:
        POST /api/groups/remove-member
        {
            "group_name": "IT-Administrators",
            "member_dn": "CN=John Smith,OU=Users,DC=domain,DC=com"
        }
    """
    manager, conn = get_group_manager()
    try:
        result = manager.remove_member(member.group_name, member.member_dn)
        return result
    finally:
        release_connection(conn)


@router.get("/user/{username}/groups")
async def get_user_groups(username: str):
    """
    Get all groups a user is member of.

    Retrieves all group memberships for a specific user, including
    direct memberships and nested group memberships through other groups.

    Args:
        username: The sAMAccountName of the user

    Returns:
        dict: Username, group list, and count

    Example Response:
        {
            "username": "jsmith",
            "groups": ["Domain-Admins", "IT-Staff", "Remote-Users"],
            "count": 3
        }
    """
    manager, conn = get_group_manager()
    try:
        groups = manager.get_user_groups(username)
        return {"username": username, "groups": groups, "count": len(groups)}
    finally:
        release_connection(conn)


@router.get("/empty")
async def get_empty_groups():
    """
    Find groups with no members.

    Identifies security or distribution groups that have no members.
    Empty groups may indicate obsolete groups that should be reviewed
    and potentially removed for security cleanup.

    Returns:
        dict: Count and list of empty groups

    Example Response:
        {
            "count": 5,
            "groups": ["Old-Project-Team", "Deprecated-All", ...]
        }
    """
    manager, conn = get_group_manager()
    try:
        groups = manager.find_empty_groups()
        return {"count": len(groups), "groups": groups}
    finally:
        release_connection(conn)


@router.post("/bulk-add/{group_name}")
async def bulk_add_members(group_name: str, members: list = Body()):
    """
    Add multiple members to a group in a single operation.

    Bulk adds multiple users or groups as members of the specified group.
    Members are processed sequentially, and partial success is possible.

    Args:
        group_name: The name (CN) of the target group
        members: List of member Distinguished Names

    Returns:
        dict: Results with success and failure counts

    Example:
        POST /api/groups/bulk-add/IT-Administrators
        [
            "CN=User1,OU=Users,DC=domain,DC=com",
            "CN=User2,OU=Users,DC=domain,DC=com",
            "CN=User3,OU=Users,DC=domain,DC=com"
        ]

    Response:
        {"success": 3, "failed": 0}
    """
    manager, conn = get_group_manager()
    try:
        result = manager.bulk_add_members(group_name, members)
        return result
    finally:
        release_connection(conn)
