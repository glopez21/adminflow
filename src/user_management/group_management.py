"""
Group Management Module for Active Directory.

This module provides comprehensive group management capabilities for AD
environments, supporting security and distribution groups with full CRUD
operations and membership management.

Classes:
    ADGroupManager: Main class for all group-related AD operations

Features:
    - Create security and distribution groups
    - Add/remove members from groups
    - Get group members list
    - Get user's group memberships
    - Find empty groups
    - Bulk member operations

Usage:
    from src.user_management.group_management import ADGroupManager
    from src.utils.ad_connection import ADConnection

    conn = ADConnection(server="dc.domain.com", ...)
    group_mgr = ADGroupManager(conn)

    # Create a new group
    result = group_mgr.create_group(
        group_name="IT-Administrators",
        group_scope="Global",
        group_type="Security",
        ou="OU=Groups,DC=domain,DC=com"
    )

    # Add a member
    group_mgr.add_member("IT-Administrators", "CN=John Smith,OU=Users,DC=domain,DC=com")

Requirements:
    - pyad library for AD operations
    - Active Directory connection with appropriate permissions
"""

import logging

logger = logging.getLogger(__name__)


class ADGroupManager:
    """
    Handles Active Directory group operations.

    This class provides a comprehensive interface for managing AD groups
    including creation, deletion, membership management, and queries.

    Attributes:
        conn: Active Directory connection instance
        pyad: pyad library reference (None if not available on non-Windows)
    """

    def __init__(self, ad_connection):
        """
        Initialize group manager with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        self.conn = ad_connection
        self.pyad = None

        try:
            import pyad

            self.pyad = pyad
        except Exception:
            logger.warning("pyad not available")

    def create_group(
        self,
        group_name: str,
        group_scope: str = "Global",
        group_type: str = "Security",
        ou: str | None = None,
    ) -> dict:
        """
        Create a new AD security or distribution group.

        Creates a new group in the specified Organizational Unit with
        the specified scope and type. Security groups are used for
        access control, while distribution groups are for email.

        Args:
            group_name: The common name (CN) for the group
            group_scope: Group scope (Global, Universal, DomainLocal)
            group_type: Group type (Security, Distribution)
            ou: Target OU DN (defaults to base_dn if not specified)

        Returns:
            dict: Success status and group name, or error message

        Group Scopes:
            - Global: Can contain users from same domain, can be nested
            - Universal: Can contain groups from any domain in forest
            - DomainLocal: Can contain users/groups from any domain

        Example:
            result = manager.create_group(
                group_name="Engineering-Team",
                group_scope="Global",
                group_type="Security",
                ou="OU=Groups,DC=domain,DC=com"
            )
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyadgroup

            if not ou:
                ou = self.conn.base_dn

            pyadgroup.create(
                name=group_name, group_scope=group_scope, group_type=group_type, ou=ou
            )

            logger.info(f"Created group: {group_name}")
            return {"status": "success", "group": group_name}

        except Exception as e:
            logger.error(f"Failed to create group {group_name}: {e}")
            return {"status": "error", "message": str(e)}

    def add_member(self, group_name: str, member_dn: str) -> dict:
        """
        Add a member to a group.

        Adds a user or another group as a member of the specified group.
        Members inherit permissions assigned to the group.

        Args:
            group_name: The name (CN) of the target group
            member_dn: Distinguished Name of the member to add

        Returns:
            dict: Success status or error message

        Example:
            result = manager.add_member(
                "IT-Administrators",
                "CN=John Smith,OU=Users,DC=domain,DC=com"
            )
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyadgroup

            group = pyadgroup.from_cn(group_name)
            group.add_members([member_dn])

            logger.info(f"Added member to group: {group_name}")
            return {"status": "success", "group": group_name}

        except Exception as e:
            logger.error(f"Failed to add member to group {group_name}: {e}")
            return {"status": "error", "message": str(e)}

    def remove_member(self, group_name: str, member_dn: str) -> dict:
        """
        Remove a member from a group.

        Removes a user or group from the specified group. The member
        loses all permissions granted by this group's membership.

        Args:
            group_name: The name (CN) of the target group
            member_dn: Distinguished Name of the member to remove

        Returns:
            dict: Success status or error message
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyadgroup

            group = pyadgroup.from_cn(group_name)
            group.remove_members([member_dn])

            logger.info(f"Removed member from group: {group_name}")
            return {"status": "success", "group": group_name}

        except Exception as e:
            logger.error(f"Failed to remove member from group {group_name}: {e}")
            return {"status": "error", "message": str(e)}

    def get_group_members(self, group_name: str) -> list[str]:
        """
        Get all members of a group.

        Retrieves all user and group members of the specified AD group.

        Args:
            group_name: The name (CN) of the group

        Returns:
            list: List of member usernames, empty list on error

        Example:
            members = manager.get_group_members("Domain-Admins")
            for member in members:
                print(f"  - {member}")
        """
        if not self.pyad:
            return []

        try:
            from pyad import pyadgroup

            group = pyadgroup.from_cn(group_name)
            members = group.get_members()

            return [m.get_attribute("sAMAccountName")[0] for m in members]

        except Exception as e:
            logger.error(f"Failed to get members of group {group_name}: {e}")
            return []

    def get_user_groups(self, username: str) -> list[str]:
        """
        Get all groups a user is member of.

        Retrieves all group memberships for a specific user, including
        both direct and nested group memberships.

        Args:
            username: The sAMAccountName of the user

        Returns:
            list: List of group names the user belongs to

        Example:
            groups = manager.get_user_groups("jsmith")
            print(f"User belongs to {len(groups)} groups")
        """
        if not self.pyad:
            return []

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)
            member_of = user.get_attribute("memberOf")

            groups = []
            for group_dn in member_of:
                group_cn = group_dn.split(",")[0].replace("CN=", "")
                groups.append(group_cn)

            return groups

        except Exception as e:
            logger.error(f"Failed to get groups for user {username}: {e}")
            return []

    def find_empty_groups(self) -> list[str]:
        """
        Find groups with no members.

        Searches the directory for security or distribution groups
        that have no members. Empty groups may indicate obsolete
        groups that should be reviewed and cleaned up.

        Returns:
            list: List of empty group names

        Example:
            empty = manager.find_empty_groups()
            print(f"Found {len(empty)} empty groups")
            for group in empty:
                print(f"  - {group}")
        """
        if not self.pyad:
            return []

        try:
            from pyad import pyadgroup

            empty_groups = []

            container = self.conn.base_dn
            all_groups = pyadgroup.PyADGroup.get_filtered_ldap_objects(
                f"CN=*,{container}", ["cn"]
            )

            for group in all_groups:
                try:
                    members = group.get_members()
                    if len(members) == 0:
                        empty_groups.append(group.get_attribute("cn")[0])
                except Exception:
                    continue

            logger.info(f"Found {len(empty_groups)} empty groups")
            return empty_groups

        except Exception as e:
            logger.error(f"Failed to find empty groups: {e}")
            return []

    def bulk_add_members(self, group_name: str, members: list[str]) -> dict:
        """
        Add multiple members to a group.

        Adds multiple users or groups as members of the specified group
        in a single operation. Processes members sequentially with
        partial success possible.

        Args:
            group_name: The name (CN) of the target group
            members: List of member Distinguished Names to add

        Returns:
            dict: Results with success and failure counts

        Example:
            result = manager.bulk_add_members(
                "IT-Team",
                [
                    "CN=User1,OU=Users,DC=domain,DC=com",
                    "CN=User2,OU=Users,DC=domain,DC=com"
                ]
            )
            print(f"Added: {result['success']}, Failed: {result['failed']}")
        """
        results = {"success": 0, "failed": 0}

        for member in members:
            result = self.add_member(group_name, member)
            if result.get("status") == "success":
                results["success"] += 1
            else:
                results["failed"] += 1

        return results
