"""
Migration API Endpoints for AdminFlow.

This module provides REST API endpoints for Active Directory migration
operations. It supports bulk user import from CSV, batch user moves between
OUs, user attribute preservation, and group mapping for migrations.

Endpoints:
    POST /api/migration/csv - Bulk migrate users from CSV file
    POST /api/migration/move - Move multiple users to new OU
    GET /api/migration/export/{username} - Export user attributes
    POST /api/migration/group-mapping - Set up group mappings
    POST /api/migration/map-groups - Map source groups to target

Authentication:
    Requires API key or JWT token with admin scopes.

Example:
    # Import users from CSV
    curl -X POST -H "X-API-Key: ad-admin-key-001" \
         -F "file=@users.csv" \
         http://localhost:8000/api/migration/csv
    
    # Move users to new OU
    curl -X POST -H "Authorization: Bearer <token>" \
         -H "Content-Type: application/json" \
         -d '["user1", "user2", "user3"]' \
         "http://localhost:8000/api/migration/move?target_ou=OU=Archive,DC=domain,DC=com"
"""

import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

import config.settings as settings
from src.migration.ad_migration import ADMigrationManager
from src.utils.ad_connection import ADConnection

logger = logging.getLogger(__name__)
router = APIRouter()


def get_migration_manager():
    """
    Create and connect a migration manager instance.

    Returns:
        tuple: (ADMigrationManager instance, AD connection)
    """
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    conn.connect()
    return ADMigrationManager(conn), conn


@router.post("/csv")
async def migrate_from_csv(file: UploadFile = File(...)):
    """
    Bulk migrate/create users from a CSV file.

    Reads a CSV file containing user data and creates corresponding
    AD accounts. The CSV should contain columns for username, first_name,
    last_name, email, password, department, title, ou, and optionally
    groups (semicolon-separated).

    Args:
        file: CSV file upload containing user data

    Returns:
        dict: Migration results with success/failure counts

    Raises:
        HTTPException: If CSV processing fails (500)

    CSV Format Example:
        username,first_name,last_name,email,password,department,title,ou,groups
        jsmith,John,Smith,jsmith@domain.com,Pass123,IT,Engineer,OU=IT,Domain-Admins;IT-Staff
        mjane,Jane,Mary,jane@domain.com,Pass456,HR,Manager,OU=HR,HR-Team
    """
    migrator, conn = get_migration_manager()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = migrator.migrate_users_from_csv(tmp_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.disconnect()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/move")
async def batch_move_users(users: list, target_ou: str):
    """
    Move multiple users to a new Organizational Unit.

    Relocates multiple user accounts to a different OU in a single
    operation. This is useful during restructuring or when archiving
    inactive users.

    Args:
        users: List of usernames to move
        target_ou: The Distinguished Name of the target OU

    Returns:
        dict: Move results with success and failure counts

    Example:
        POST /api/migration/move?target_ou=OU=Archive,DC=domain,DC=com
        Body: ["user1", "user2", "user3"]

    Response:
        {
            "success": ["user1", "user2"],
            "failed": [{"username": "user3", "error": "..."}]
        }
    """
    migrator, conn = get_migration_manager()
    try:
        result = migrator.batch_move_users(users, target_ou)
        return result
    finally:
        conn.disconnect()


@router.get("/export/{username}")
async def export_user_attributes(username: str):
    """
    Export all attributes of a user for migration preservation.

    Extracts comprehensive user account attributes including contact
    info, department, title, company, manager, group memberships,
    and profile settings. This data can be used to recreate the user
    in a different domain or for backup purposes.

    Args:
        username: The sAMAccountName of the user to export

    Returns:
        dict: User attributes and their values

    Example Response:
        {
            "status": "success",
            "username": "jsmith",
            "attributes": {
                "sAMAccountName": "jsmith",
                "mail": "jsmith@domain.com",
                "displayName": "John Smith",
                "department": "Engineering",
                "title": "Software Engineer",
                "memberOf": ["Domain-Admins", "IT-Staff"],
                ...
            }
        }
    """
    migrator, conn = get_migration_manager()
    try:
        result = migrator.preserve_user_attributes(username)
        return result
    finally:
        conn.disconnect()


@router.post("/group-mapping")
async def create_group_mapping(mappings: dict):
    """
    Set up group mappings for migration.

    Stores a mapping dictionary that translates source domain
    group names to target domain group names. This is used
    during migration to recreate group memberships in the
    target environment.

    Args:
        mappings: Dictionary mapping source group names to target group names

    Returns:
        dict: Success status and mapping count

    Example:
        POST /api/migration/group-mapping
        {
            "Domain-Admins": "Enterprise-Admins",
            "IT-Staff": "IT-Team",
            "HR-Users": "HR-Group"
        }
    """
    migrator, conn = get_migration_manager()
    try:
        migrator.create_group_mapping(mappings)
        return {"status": "success", "mappings_count": len(mappings)}
    finally:
        conn.disconnect()


@router.post("/map-groups")
async def map_source_groups(source_groups: list, target_ou: str):
    """
    Map source domain groups to target domain.

    Uses the previously stored group mappings to create or find
    corresponding groups in the target domain. Creates new groups
    if they don't exist in the target.

    Args:
        source_groups: List of source group names to map
        target_ou: OU where new groups should be created if needed

    Returns:
        dict: Mapping results with success and failure counts

    Example:
        POST /api/migration/map-groups?target_ou=OU=Groups,DC=domain,DC=com
        Body: ["Domain-Admins", "IT-Staff"]
    """
    migrator, conn = get_migration_manager()
    try:
        result = migrator.map_source_groups(source_groups, target_ou)
        return result
    finally:
        conn.disconnect()
