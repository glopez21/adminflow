"""
Migration Tools for Active Directory.

This module provides comprehensive migration capabilities for AD environments,
including bulk user import from CSV, batch operations, attribute preservation,
and group mapping between source and target domains.

Classes:
    ADMigrationManager: Main class handling all migration operations

Features:
    - CSV-based bulk user creation
    - Batch user moves between OUs
    - User attribute extraction for preservation
    - Group mapping for domain migrations
    - Migration report generation

Usage:
    from src.migration.ad_migration import ADMigrationManager
    from src.utils.ad_connection import ADConnection

    conn = ADConnection(server="dc.domain.com", ...)
    migrator = ADMigrationManager(conn)

    # Import users from CSV
    result = migrator.migrate_users_from_csv("users.csv")

    # Move users to new OU
    result = migrator.batch_move_users(["user1", "user2"], "OU=Archive,DC=domain,DC=com")

Requirements:
    - pyad library for AD operations
    - CSV file with user data
"""

import csv
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ADMigrationManager:
    """
    Handles Active Directory migration tasks.

    This class provides methods for migrating users between OUs,
    importing users from external sources, and preserving user
    attributes during migration operations.

    Attributes:
        conn: Active Directory connection instance
        pyad: pyad library reference (None if not available)
        group_mappings: Dictionary for source-to-target group mappings
    """

    def __init__(self, ad_connection):
        """
        Initialize migration manager with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        self.conn = ad_connection
        self.pyad = None

        try:
            import pyad

            self.pyad = pyad
        except Exception:
            logger.warning("pyad not available - migration functionality limited")

    def migrate_users_from_csv(self, csv_file: str) -> dict:
        """
        Bulk migrate or create users from CSV file.

        Reads a CSV file containing user data and creates corresponding
        AD accounts. Supports optional group assignment during creation.

        Args:
            csv_file: Path to CSV file with user data

        Returns:
            dict: Migration results with lists of migrated and failed users

        CSV Format:
            username,first_name,last_name,email,password,department,title,ou,groups
            jsmith,John,Smith,jsmith@domain.com,Pass123,IT,Engineer,OU=IT,Group1;Group2
        """
        migrated = []
        failed = []

        try:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                users = list(reader)

            for user in users:
                try:
                    result = self._migrate_single_user(user)
                    if result.get("status") == "success":
                        migrated.append(user.get("username"))
                    else:
                        failed.append(
                            {
                                "username": user.get("username"),
                                "error": result.get("message"),
                            }
                        )
                except Exception as e:
                    failed.append({"username": user.get("username"), "error": str(e)})

            logger.info(
                f"Migration complete: {len(migrated)} success, {len(failed)} failed"
            )
            return {
                "migrated": migrated,
                "failed": failed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"CSV migration failed: {e}")
            return {"status": "error", "message": str(e)}

    def _migrate_single_user(self, user_data: dict) -> dict:
        """
        Migrate a single user with all attributes.

        Creates a new AD user with the provided attributes and optionally
        adds the user to specified groups.

        Args:
            user_data: Dictionary with user attributes from CSV

        Returns:
            dict: Success status and username or error message
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            new_user = pyaduser.create(
                name=f"{user_data.get('first_name')} {user_data.get('last_name')}",
                sAMAccountName=user_data.get("username"),
                password=user_data.get("password", "ChangeMe123!"),
                enabled=True,
                optional_attributes={
                    "mail": user_data.get("email"),
                    "givenName": user_data.get("first_name"),
                    "sn": user_data.get("last_name"),
                    "displayName": f"{user_data.get('first_name')} {user_data.get('last_name')}",
                    "department": user_data.get("department", ""),
                    "title": user_data.get("title", ""),
                    "telephoneNumber": user_data.get("phone", ""),
                    "company": user_data.get("company", ""),
                    "physicalDeliveryOfficeName": user_data.get("office", ""),
                },
                ou=user_data.get("ou", self.conn.base_dn),
            )

            groups_str = user_data.get("groups")
            if groups_str:
                groups = str(groups_str).split(";")
                for group in groups:
                    try:
                        from pyad import pyadgroup

                        g = pyadgroup.from_cn(group.strip())
                        g.add_members([str(new_user.dn)])
                    except Exception:
                        logger.warning(f"Could not add user to group: {group}")

            return {"status": "success", "user": user_data.get("username")}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_group_mapping(self, mappings: dict[str, str]) -> None:
        """
        Store group mappings for migration.

        Saves a dictionary mapping source domain group names to their
        corresponding names in the target domain. Used during group
        migration to translate memberships.

        Args:
            mappings: Dictionary mapping source group names to target names

        Example:
            mappings = {
                "Domain-Admins": "Enterprise-Admins",
                "IT-Staff": "IT-Team"
            }
        """
        self.group_mappings = mappings
        logger.info(f"Created {len(mappings)} group mappings")

    def map_source_groups(self, source_groups: list[str], target_ou: str) -> dict:
        """
        Map source domain groups to target domain.

        Uses stored group mappings to find or create corresponding groups
        in the target domain. Creates new groups if they don't exist.

        Args:
            source_groups: List of source group names to map
            target_ou: OU where new groups should be created if needed

        Returns:
            dict: Mapping results with success and failure counts
        """
        results: dict[str, list] = {"mapped": [], "failed": []}

        for source_group in source_groups:
            target_group = self.group_mappings.get(source_group, source_group)

            try:
                from pyad import pyadgroup

                try:
                    pyadgroup.from_cn(target_group)
                    results["mapped"].append(
                        {"source": source_group, "target": target_group}
                    )
                except Exception:
                    pyadgroup.create(
                        name=target_group,
                        group_scope="Global",
                        group_type="Security",
                        ou=target_ou,
                    )
                    results["mapped"].append(
                        {
                            "source": source_group,
                            "target": target_group,
                            "created": True,
                        }
                    )

            except Exception as e:
                results["failed"].append({"source": source_group, "error": str(e)})

        return results

    def batch_move_users(self, users: list[str], target_ou: str) -> dict:
        """
        Move multiple users to a new Organizational Unit.

        Relocates multiple user accounts to a different OU in a single
        operation. This is useful for restructuring or archiving.

        Args:
            users: List of usernames to move
            target_ou: The Distinguished Name of the target OU

        Returns:
            dict: Move results with success and failure counts
        """
        results: dict[str, list] = {"success": [], "failed": []}

        for username in users:
            try:
                from pyad import pyaduser

                user = pyaduser.from_cn(username)
                user.move(target_ou)
                results["success"].append(username)

            except Exception as e:
                results["failed"].append({"username": username, "error": str(e)})

        logger.info(
            f"Batch move: {len(results['success'])} success, {len(results['failed'])} failed"
        )
        return results

    def preserve_user_attributes(self, username: str) -> dict:
        """
        Extract all user attributes for preservation.

        Retrieves comprehensive user account attributes that can be
        used for backup or migration to another domain.

        Args:
            username: The sAMAccountName of the user

        Returns:
            dict: User attributes and their values

        Extracted Attributes:
            sAMAccountName, mail, displayName, department, title,
            company, telephoneNumber, physicalDeliveryOfficeName,
            manager, memberOf, homeDirectory, profilePath, etc.
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyaduser

            user = pyaduser.from_cn(username)

            attributes = user.get_attributes(
                [
                    "sAMAccountName",
                    "mail",
                    "displayName",
                    "department",
                    "title",
                    "company",
                    "telephoneNumber",
                    "physicalDeliveryOfficeName",
                    "manager",
                    "memberOf",
                    "homeDirectory",
                    "profilePath",
                    "scriptPath",
                    "homeDrive",
                ]
            )

            return {"status": "success", "username": username, "attributes": attributes}

        except Exception as e:
            logger.error(f"Failed to preserve attributes for {username}: {e}")
            return {"status": "error", "message": str(e)}

    def export_migration_report(self, results: dict, output_file: str) -> None:
        """
        Export migration results to CSV.

        Creates a CSV file with the results of a migration operation,
        including status, username, error details, and timestamp.

        Args:
            results: Migration results dictionary
            output_file: Path for the output CSV file
        """
        try:
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Status", "Username", "Details", "Timestamp"])

                for user in results.get("migrated", []):
                    writer.writerow(["Success", user, "", results.get("timestamp", "")])

                for user in results.get("failed", []):
                    writer.writerow(
                        [
                            "Failed",
                            user.get("username"),
                            user.get("error"),
                            results.get("timestamp", ""),
                        ]
                    )

            logger.info(f"Migration report exported to {output_file}")

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
