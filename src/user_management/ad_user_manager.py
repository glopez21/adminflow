"""
User Management Module for Active Directory.

This module provides comprehensive user account management capabilities
for Active Directory environments. It supports creating, modifying,
enabling/disabling, password management, and querying user accounts.

Classes:
    ADUserManager: Main class for all user-related AD operations

Features:
    - Create new user accounts with full attribute set
    - Enable/disable user accounts
    - Password reset operations
    - Move users between OUs
    - Retrieve detailed user information
    - Find inactive users
    - Bulk user creation

Usage:
    from src.user_management.ad_user_manager import ADUserManager
    from src.utils.ad_connection import ADConnection

    conn = ADConnection(server="dc.domain.com", ...)
    user_mgr = ADUserManager(conn)

    # Create a new user
    result = user_mgr.create_user(
        username="jsmith",
        first_name="John",
        last_name="Smith",
        email="jsmith@domain.com",
        password="SecurePass123!",
        ou="OU=Users,DC=domain,DC=com",
        department="IT",
        title="Systems Administrator"
    )

Requirements:
    - pyad library for AD operations
    - Active Directory connection with appropriate permissions
"""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

if os.name == "nt":
    try:
        import pyad
    except Exception:
        pyad = None
        logger.warning("pyad not available - limited functionality")
else:
    pyad = None
    logger.warning("pyad not available on non-Windows platforms - limited functionality")


class ADUserManager:
    """
    Handles Active Directory user operations.

    This class provides a comprehensive interface for managing AD user
    accounts including creation, modification, disable/enable, password
    reset, moves, and querying operations.

    Attributes:
        conn: Active Directory connection instance
        pyad: pyad library reference (None if not available on non-Windows)
    """

    def __init__(self, ad_connection):
        """
        Initialize user manager with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        self.conn = ad_connection
        self.pyad = pyad

    def create_user(
        self,
        username: str,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        ou: str,
        department: str | None = None,
        title: str | None = None,
        enabled: bool = True,
    ) -> dict:
        """
        Create a new AD user account.

        Creates a new user in the specified Organizational Unit with
        the provided attributes. Optionally sets department and title.

        Args:
            username: The sAMAccountName (logon name)
            first_name: User's given name
            last_name: User's surname
            email: User's email address
            password: Initial password
            ou: Target Organizational Unit DN
            department: User's department (optional)
            title: User's job title (optional)
            enabled: Whether account should be enabled (default: True)

        Returns:
            dict: Success status and user DN, or error message

        Example:
            result = manager.create_user(
                username="jsmith",
                first_name="John",
                last_name="Smith",
                email="jsmith@domain.com",
                password="SecurePass123!",
                ou="OU=IT,DC=domain,DC=com",
                department="Engineering",
                title="Software Engineer"
            )
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            new_user = pyaduser.create(
                name=f"{first_name} {last_name}",
                sAMAccountName=username,
                password=password,
                enabled=enabled,
                optional_attributes={
                    "mail": email,
                    "givenName": first_name,
                    "sn": last_name,
                    "displayName": f"{first_name} {last_name}",
                    "userPrincipalName": f"{username}@{self.conn.server.split('.')[-2:]}"
                    if "." in self.conn.server
                    else f"{username}@domain.local",
                },
                ou=ou,
            )

            if department:
                new_user.update_attribute("department", department)
            if title:
                new_user.update_attribute("title", title)

            logger.info(f"Created user: {username}")
            return {"status": "success", "user": username, "dn": str(new_user.dn)}

        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return {"status": "error", "message": str(e)}

    def disable_user(self, username: str) -> dict:
        """
        Disable an AD user account.

        Disables a user account while preserving it in the directory.
        The user cannot authenticate but the account remains.

        Args:
            username: The sAMAccountName of the user to disable

        Returns:
            dict: Success status or error message
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)
            user.disable()

            logger.info(f"Disabled user: {username}")
            return {"status": "success", "user": username}

        except Exception as e:
            logger.error(f"Failed to disable user {username}: {e}")
            return {"status": "error", "message": str(e)}

    def enable_user(self, username: str) -> dict:
        """
        Enable an AD user account.

        Re-enables a previously disabled user account, restoring
        the ability to authenticate.

        Args:
            username: The sAMAccountName of the user to enable

        Returns:
            dict: Success status or error message
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)
            user.enable()

            logger.info(f"Enabled user: {username}")
            return {"status": "success", "user": username}

        except Exception as e:
            logger.error(f"Failed to enable user {username}: {e}")
            return {"status": "error", "message": str(e)}

    def reset_password(self, username: str, new_password: str) -> dict:
        """
        Reset a user's password.

        Sets a new password for the specified user. The user's
        password policy may require password change on next logon.

        Args:
            username: The sAMAccountName of the user
            new_password: The new password to set

        Returns:
            dict: Success status or error message
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)
            user.set_password(new_password)

            logger.info(f"Password reset for user: {username}")
            return {"status": "success", "user": username}

        except Exception as e:
            logger.error(f"Failed to reset password for {username}: {e}")
            return {"status": "error", "message": str(e)}

    def move_user(self, username: str, new_ou: str) -> dict:
        """
        Move user to a different Organizational Unit.

        Relocates a user account to a different OU while preserving
        all attributes and group memberships.

        Args:
            username: The sAMAccountName of the user to move
            new_ou: The Distinguished Name of the target OU

        Returns:
            dict: Success status with new OU or error message

        Example:
            result = manager.move_user("jsmith", "OU=Archive,DC=domain,DC=com")
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)
            user.move(new_ou)

            logger.info(f"Moved user {username} to {new_ou}")
            return {"status": "success", "user": username, "new_ou": new_ou}

        except Exception as e:
            logger.error(f"Failed to move user {username}: {e}")
            return {"status": "error", "message": str(e)}

    def get_user_info(self, username: str) -> dict:
        """
        Get detailed user account information.

        Retrieves comprehensive user account attributes including
        contact info, department, title, status, creation date,
        and last logon timestamp.

        Args:
            username: The sAMAccountName of the user

        Returns:
            dict: User information or error message

        Attributes Retrieved:
            sAMAccountName, mail, displayName, department, title,
            enabled, whenCreated, lastLogonTimestamp, pwdLastSet, memberOf
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)

            attributes = [
                "sAMAccountName",
                "mail",
                "displayName",
                "department",
                "title",
                "enabled",
                "whenCreated",
                "lastLogonTimestamp",
                "pwdLastSet",
                "memberOf",
            ]

            info = {"username": username}
            for attr in attributes:
                try:
                    value = user.get_attribute(attr)
                    if value:
                        info[attr] = value[0] if len(value) == 1 else value
                except Exception:
                    pass

            return {"status": "success", "user": info}

        except Exception as e:
            logger.error(f"Failed to get user info for {username}: {e}")
            return {"status": "error", "message": str(e)}

    def find_inactive_users(self, days: int = 90) -> list[dict]:
        """
        Find users who haven't logged in for specified days.

        Queries the directory for user accounts with lastLogonTimestamp
        older than the specified threshold. These accounts may be
        candidates for disablement or removal.

        Args:
            days: Number of days of inactivity (default: 90)

        Returns:
            list: List of inactive users with username, last logon, email

        Example:
            # Find users inactive for 6 months
            inactive = manager.find_inactive_users(180)
            for user in inactive:
                print(f"{user['username']} - last logon: {user['last_logon']}")
        """
        if not self.pyad:
            return [{"status": "error", "message": "pyad not available"}]

        try:
            from datetime import timedelta

            from pyad import pyadcontainer

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            inactive_users = []

            ou = pyadcontainer.PyADContainer.from_dn(self.conn.base_dn)

            for user in ou.get_children():
                try:
                    last_logon = user.get_attribute("lastLogonTimestamp")
                    if last_logon and last_logon[0] < cutoff_date:
                        inactive_users.append(
                            {
                                "username": user.get_attribute("sAMAccountName")[0],
                                "last_logon": str(last_logon[0]),
                                "email": user.get_attribute("mail")[0]
                                if user.get_attribute("mail")
                                else None,
                            }
                        )
                except Exception:
                    continue

            logger.info(f"Found {len(inactive_users)} inactive users")
            return inactive_users

        except Exception as e:
            logger.error(f"Failed to find inactive users: {e}")
            return []

    def bulk_create_users(self, users: list[dict]) -> dict:
        """
        Create multiple users from a list.

        Iterates through a list of user dictionaries and creates
        each user in AD. Partial success is possible - some users
        may succeed while others fail.

        Args:
            users: List of user dictionaries with required fields

        Returns:
            dict: Results with success and failure counts

        Expected User Dict:
            username, first_name, last_name, email, password, ou,
            department (optional), title (optional)
        """
        results: dict[str, list] = {"success": [], "failed": []}

        for user_data in users:
            result = self.create_user(
                username=user_data.get("username") or "",
                first_name=user_data.get("first_name") or "",
                last_name=user_data.get("last_name") or "",
                email=user_data.get("email") or "",
                password=user_data.get("password") or "",
                ou=user_data.get("ou", self.conn.base_dn),
                department=user_data.get("department"),
                title=user_data.get("title"),
            )

            if result.get("status") == "success":
                results["success"].append(user_data.get("username"))
            else:
                results["failed"].append(
                    {
                        "username": user_data.get("username"),
                        "error": result.get("message"),
                    }
                )

        logger.info(
            f"Bulk user creation: {len(results['success'])} success, {len(results['failed'])} failed"
        )
        return results
