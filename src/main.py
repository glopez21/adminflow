"""
Main entry point for the AdminFlow AD automation system.

This module provides a command-line interface (CLI) for managing Active Directory
through various subcommands. It serves as the primary entry point for script-based
or manual operations where a REST API is not required.

Usage:
    python -m src.main <command> <action> [options]

Commands:
    user    - User management operations (create, disable, enable, info, inactive)
    group   - Group management operations (create, members, add-member)
    health  - AD health checks (all, replication, dc, ldap, fsmo)
    security- Security audits (all, privileged, password, inactive, locked)
    migrate - Migration tools (csv, move)

Example:
    python -m src.main user create --username jsmith --first-name John \\
            --last-name Smith --email jsmith@domain.com --department IT
"""

import argparse

import config.settings as settings
from src.health_checks.ad_health import ADHealthChecker
from src.migration.ad_migration import ADMigrationManager
from src.security.ad_security import ADSecurityAuditor
from src.user_management.ad_user_manager import ADUserManager
from src.user_management.group_management import ADGroupManager
from src.utils.ad_connection import ADConnection
from src.utils.logger import setup_logging


def parse_args():
    """
    Parse command-line arguments and return namespace object.

    This function sets up the argument parser with subcommands for different
    operations. Each subcommand has its own set of options and arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing command and options
    """
    # Create main parser with description
    parser = argparse.ArgumentParser(
        description="AdminFlow - AD Automation System CLI",
        epilog="Run 'python -m src.main <command> --help' for more info on each command",
    )

    # Add subparsers for different operation categories
    # Each subcommand handles a specific domain of AD management
    subparsers = parser.add_subparsers(
        dest="command", help="Available command categories"
    )

    # ---------------------------------------------------------------------
    # USER MANAGEMENT COMMANDS
    # ---------------------------------------------------------------------
    # The 'user' subcommand handles all user-related operations including
    # creating new users, modifying existing ones, and searching for users
    # based on various criteria.
    user_parser = subparsers.add_parser(
        "user", help="User management: create, disable, enable, info, inactive"
    )
    user_parser.add_argument(
        "action",
        choices=["create", "disable", "enable", "info", "inactive"],
        help="User operation to perform",
    )
    user_parser.add_argument("--username", help="Username (sAMAccountName)")
    user_parser.add_argument("--first-name", help="User's first name (givenName)")
    user_parser.add_argument("--last-name", help="User's last name (sn)")
    user_parser.add_argument("--email", help="Email address (mail)")
    user_parser.add_argument("--password", help="User password")
    user_parser.add_argument("--ou", help="Target Organizational Unit DN")
    user_parser.add_argument("--department", help="Department attribute")
    user_parser.add_argument("--title", help="Job title (title attribute)")
    user_parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days for inactive account detection (default: 90)",
    )

    # ---------------------------------------------------------------------
    # GROUP MANAGEMENT COMMANDS
    # ---------------------------------------------------------------------
    # The 'group' subcommand handles Active Directory group operations
    # including creating groups, managing membership, and querying groups.
    group_parser = subparsers.add_parser(
        "group", help="Group management: create, members, add-member"
    )
    group_parser.add_argument(
        "action",
        choices=["create", "members", "add-member"],
        help="Group operation to perform",
    )
    group_parser.add_argument("--name", help="Group name (common name)")
    group_parser.add_argument("--member", help="Member Distinguished Name (DN)")
    group_parser.add_argument("--ou", help="Organizational Unit for new group")

    # ---------------------------------------------------------------------
    # HEALTH CHECK COMMANDS
    # ---------------------------------------------------------------------
    # The 'health' subcommand runs various Active Directory health checks
    # to verify the status of domain controllers, replication, and other
    # critical infrastructure components.
    health_parser = subparsers.add_parser(
        "health", help="Health checks: all, replication, dc, ldap, fsmo"
    )
    health_parser.add_argument(
        "check",
        choices=["all", "replication", "dc", "ldap", "fsmo"],
        help="Health check to perform",
    )

    # ---------------------------------------------------------------------
    # SECURITY AUDIT COMMANDS
    # ---------------------------------------------------------------------
    # The 'security' subcommand performs security audits of the Active
    # Directory environment, identifying privileged accounts, password
    # policy violations, inactive accounts, and locked accounts.
    security_parser = subparsers.add_parser(
        "security", help="Security audits: all, privileged, password, inactive, locked"
    )
    security_parser.add_argument(
        "audit",
        choices=["all", "privileged", "password", "inactive", "locked"],
        help="Security audit to perform",
    )
    security_parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days threshold for inactive account checks (default: 90)",
    )

    # ---------------------------------------------------------------------
    # MIGRATION COMMANDS
    # ---------------------------------------------------------------------
    # The 'migrate' subcommand handles user migration operations including
    # bulk importing from CSV files and batch moving users between OUs.
    migration_parser = subparsers.add_parser(
        "migrate", help="Migration tools: csv import, batch move"
    )
    migration_parser.add_argument(
        "action", choices=["csv", "move"], help="Migration operation to perform"
    )
    migration_parser.add_argument("--file", help="CSV file for migration")
    migration_parser.add_argument("--target-ou", help="Target OU DN for move operation")
    migration_parser.add_argument(
        "--users", nargs="+", help="List of usernames to move"
    )

    return parser.parse_args()


def main():
    """
    Main entry point for the CLI application.

    This function:
    1. Parses command-line arguments
    2. Initializes logging
    3. Establishes AD connection
    4. Routes to appropriate handler based on command
    5. Executes the requested operation
    6. Cleans up resources (disconnects from AD)

    The function uses a pattern of creating a connection, performing
    operations, and ensuring cleanup happens in the finally block.
    """
    # Step 1: Parse command-line arguments
    args = parse_args()

    # Step 2: Initialize logging system
    # This sets up file and console logging based on settings
    setup_logging(settings.LOG_FILE)

    # Step 3: Create and establish AD connection
    # The connection is configured with settings from config/settings.py
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )

    # Establish connection to Active Directory
    # If connection fails, subsequent operations will fail gracefully
    conn.connect()

    try:
        # Step 4: Route to appropriate handler based on command
        # Each command category has its own manager class that handles
        # the business logic for that domain.

        # -----------------------------------------------------------------
        # USER MANAGEMENT HANDLER
        # -----------------------------------------------------------------
        if args.command == "user":
            # Create user manager instance with AD connection
            user_mgr = ADUserManager(conn)

            if args.action == "create":
                # Create new AD user account
                # Requires: username, first_name, last_name, email
                # Optional: password, ou, department, title
                result = user_mgr.create_user(
                    username=args.username,
                    first_name=args.first_name,
                    last_name=args.last_name,
                    email=args.email,
                    password=args.password or "ChangeMe123!",
                    ou=args.ou or settings.DEFAULT_OU,
                    department=args.department,
                    title=args.title,
                )
                print(result)

            elif args.action == "disable":
                # Disable an existing user account
                # The account remains in AD but cannot authenticate
                result = user_mgr.disable_user(args.username)
                print(result)

            elif args.action == "enable":
                # Enable a previously disabled account
                result = user_mgr.enable_user(args.username)
                print(result)

            elif args.action == "info":
                # Retrieve detailed information about a user
                result = user_mgr.get_user_info(args.username)
                print(result)

            elif args.action == "inactive":
                # Find users who haven't logged in for specified days
                # Useful for identifying stale accounts for cleanup
                inactive = user_mgr.find_inactive_users(args.days)
                print(f"Found {len(inactive)} inactive users")
                for u in inactive:
                    print(f"  - {u.get('username')}")

        # -----------------------------------------------------------------
        # GROUP MANAGEMENT HANDLER
        # -----------------------------------------------------------------
        elif args.command == "group":
            group_mgr = ADGroupManager(conn)

            if args.action == "create":
                # Create a new security or distribution group
                result = group_mgr.create_group(args.name, ou=args.ou)
                print(result)

            elif args.action == "members":
                # List all members of a specific group
                members = group_mgr.get_group_members(args.name)
                print(f"Members of {args.name}: {members}")

            elif args.action == "add-member":
                # Add an existing user or group as a member
                result = group_mgr.add_member(args.name, args.member)
                print(result)

        # -----------------------------------------------------------------
        # HEALTH CHECK HANDLER
        # -----------------------------------------------------------------
        elif args.command == "health":
            health_checker = ADHealthChecker(conn)

            if args.check == "all":
                # Run comprehensive health check covering all areas
                result = health_checker.generate_health_report()
                print(result)

            elif args.check == "replication":
                # Check AD replication status between DCs
                # Identifies replication failures or latency issues
                result = health_checker.check_replication()
                print(result)

            elif args.check == "dc":
                # List all domain controllers in the environment
                dcs = health_checker.check_domain_controllers()
                print(dcs)

            elif args.check == "ldap":
                # Test LDAP connectivity to domain controllers
                # Verifies that LDAP ports are accessible
                result = health_checker.check_ldap_connectivity()
                print(result)

            elif args.check == "fsmo":
                # Check Flexible Single Master Operations roles
                # Identifies which DC holds each FSMO role
                result = health_checker.check_fsmo_roles()
                print(result)

        # -----------------------------------------------------------------
        # SECURITY AUDIT HANDLER
        # -----------------------------------------------------------------
        elif args.command == "security":
            auditor = ADSecurityAuditor(conn)

            if args.audit == "all":
                # Run comprehensive security audit
                result = auditor.generate_security_report()
                print(result)

            elif args.audit == "privileged":
                # Find accounts with privileged group memberships
                # Important for access review and compliance
                privileged = auditor.find_privileged_accounts()
                print(f"Found {len(privileged)} privileged accounts")
                for u in privileged:
                    print(f"  - {u.get('username')} ({u.get('group')})")

            elif args.audit == "password":
                # Check password policy compliance
                # Evaluates password settings against policy requirements
                result = auditor.check_password_policy_compliance()
                print(result)

            elif args.audit == "inactive":
                # Find accounts inactive beyond threshold
                inactive = auditor.find_inactive_accounts(90)
                print(f"Found {len(inactive)} inactive accounts")

            elif args.audit == "locked":
                # Find accounts that are currently locked out
                # May indicate brute force attempts
                locked = auditor.find_locked_accounts()
                print(f"Found {len(locked)} locked accounts")

        # -----------------------------------------------------------------
        # MIGRATION HANDLER
        # -----------------------------------------------------------------
        elif args.command == "migrate":
            migrator = ADMigrationManager(conn)

            if args.action == "csv":
                # Bulk import users from CSV file
                # CSV should contain: username, first_name, last_name, email,
                # password, department, title, ou, groups
                result = migrator.migrate_users_from_csv(args.file)
                print(result)

            elif args.action == "move":
                # Move multiple users to a new OU in one operation
                result = migrator.batch_move_users(args.users, args.target_ou)
                print(result)

        # -----------------------------------------------------------------
        # NO COMMAND SPECIFIED
        # -----------------------------------------------------------------
        else:
            # User ran the script without specifying a command
            print("No command specified. Use --help for usage information.")

    # Step 5: Cleanup - always disconnect from AD
    finally:
        conn.disconnect()


# Standard Python entry point pattern
# This allows the module to be run directly with: python -m src.main
if __name__ == "__main__":
    main()
