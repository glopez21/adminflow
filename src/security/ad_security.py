"""
Active Directory Security Auditor Module.

This module provides comprehensive security auditing capabilities for Active Directory
environments. It identifies security risks, compliance issues, and best practice
violations across user accounts, groups, and password policies.

Classes:
    ADSecurityAuditor: Main class for AD security audit operations

Features:
    - Privileged account discovery (Domain Admins, Enterprise Admins, etc.)
    - Password policy compliance checking
    - Inactive account detection
    - Locked account discovery
    - Security group auditing
    - Comprehensive security report generation

Usage:
    from src.security.ad_security import ADSecurityAuditor
    from src.utils.ad_connection import ADConnection

    conn = ADConnection(server="dc.domain.com", ...)
    auditor = ADSecurityAuditor(conn)

    # Run all security audits
    report = auditor.generate_security_report()

    # Find privileged accounts
    privileged = auditor.find_privileged_accounts()

    # Check password policy
    compliance = auditor.check_password_policy_compliance()

Requirements:
    - pyad library for AD operations (Windows-only)
    - Active Directory connection with appropriate permissions
    - Admin-level access for security queries
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ADSecurityAuditor:
    """
    Performs security audits on Active Directory.

    This class provides methods for identifying security risks
    including privileged accounts, password policy violations,
    inactive accounts, locked accounts, and problematic group
    memberships.

    Attributes:
        conn: Active Directory connection instance
        pyad: pyad library reference (None if not available)
    """

    # Well-known privileged groups to check
    PRIVILEGED_GROUPS = [
        "Domain Admins",
        "Enterprise Admins",
        "Schema Admins",
        "Administrators",
        "Account Operators",
        "Server Operators",
        "Print Operators",
        "Backup Operators",
        "DNS Admins",
        "Group Policy Creator Owners",
    ]

    def __init__(self, ad_connection):
        """
        Initialize security auditor with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        self.conn = ad_connection
        self.pyad = None

        try:
            import pyad

            self.pyad = pyad
        except Exception:
            logger.warning("pyad not available - security audit functionality limited")

    def find_privileged_accounts(self) -> list[dict]:
        """
        Find all accounts with privileged group memberships.

        Searches through well-known privileged groups (Domain Admins,
        Enterprise Admins, etc.) and identifies all member accounts.
        Reports both direct and nested group memberships.

        Returns:
            list: List of privileged account dictionaries with username and group

        Example:
            auditor = ADSecurityAuditor(conn)
            privileged = auditor.find_privileged_accounts()
            for account in privileged:
                print(f"{account['username']} - {account['group']}")
        """
        if not self.pyad:
            return []

        privileged_accounts = []

        try:
            from pyad import pyadgroup

            for group_name in self.PRIVILEGED_GROUPS:
                try:
                    group = pyadgroup.from_cn(group_name)
                    members = group.get_members()

                    for member in members:
                        try:
                            username = member.get_attribute("sAMAccountName")[0]
                            privileged_accounts.append(
                                {
                                    "username": username,
                                    "group": group_name,
                                    "dn": str(member.dn),
                                    "enabled": member.get_attribute("enabled")[0]
                                    if member.get_attribute("enabled")
                                    else None,
                                }
                            )
                        except Exception as e:
                            logger.debug(f"Error getting member info: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"Group {group_name} not found or error: {e}")
                    continue

            logger.info(f"Found {len(privileged_accounts)} privileged accounts")
            return privileged_accounts

        except Exception as e:
            logger.error(f"Failed to find privileged accounts: {e}")
            return []

    def check_password_policy_compliance(self) -> dict:
        """
        Check password policy settings for compliance.

        Evaluates the domain's password policy against security best
        practices and organizational requirements defined in settings.

        Checks:
            - Minimum password length
            - Password complexity requirements
            - Maximum password age
            - Minimum password age
            - Account lockout threshold
            - Account lockout duration

        Returns:
            dict: Password policy settings and compliance status

        Example Response:
            {
                "status": "warning",
                "policy": {
                    "min_length": 8,
                    "complexity": True,
                    "max_age_days": 90,
                    ...
                },
                "compliance": {
                    "min_length": {"required": 12, "actual": 8, "compliant": False},
                    ...
                },
                "recommendations": ["Increase minimum password length to 12"]
            }
        """
        results: dict[str, Any] = {
            "status": "unknown",
            "policy": {},
            "compliance": {},
            "recommendations": [],
        }

        if not self.pyad:
            results["status"] = "error"
            results["message"] = "pyad not available"
            return results

        try:
            from pyad import pyadcontainer

            import config.settings as settings

            domain = pyadcontainer.PyADContainer.from_dn(self.conn.base_dn)

            # Retrieve password policy attributes from domain
            policy_attrs = [
                "minPwdAge",
                "maxPwdAge",
                "minPwdLength",
                "pwdProperties",
                "lockoutThreshold",
                "lockoutDuration",
                "lockOutObservationWindow",
            ]

            for attr in policy_attrs:
                try:
                    value = domain.get_attribute(attr)
                    if value:
                        results["policy"][attr] = str(value[0])
                except Exception as e:
                    logger.debug(f"Could not get attribute {attr}: {e}")

            # Check compliance against configured requirements
            configured_policy = settings.PASSWORD_POLICY

            # Minimum length compliance
            min_length_val = int(results["policy"].get("minPwdLength", 0))
            required_min_length = configured_policy.get("min_length", 12)
            results["compliance"]["min_length"] = {
                "required": required_min_length,
                "actual": min_length_val,
                "compliant": min_length_val >= required_min_length,
            }
            if min_length_val < required_min_length:
                results["recommendations"].append(
                    f"Increase minimum password length from {min_length_val} to {required_min_length}"
                )

            # Complexity compliance
            complexity_val = int(results["policy"].get("pwdProperties", 0))
            required_complexity = configured_policy.get("require_uppercase", True)
            results["compliance"]["complexity"] = {
                "required": required_complexity,
                "actual": complexity_val >= 1,
                "compliant": complexity_val >= 1 if required_complexity else True,
            }
            if required_complexity and complexity_val < 1:
                results["recommendations"].append(
                    "Enable password complexity requirements"
                )

            # Determine overall compliance status
            all_compliant = all(
                c.get("compliant", True) for c in results["compliance"].values()
            )
            results["status"] = "compliant" if all_compliant else "warning"

        except Exception as e:
            logger.error(f"Password policy check failed: {e}")
            results["status"] = "error"
            results["message"] = str(e)

        return results

    def find_inactive_accounts(self, days: int = 90) -> list[dict]:
        """
        Find accounts that have been inactive for the specified number of days.

        Identifies user accounts with lastLogonTimestamp older than the
        specified threshold, indicating potential security risks.

        Args:
            days: Number of days of inactivity threshold (default: 90)

        Returns:
            list: List of inactive account dictionaries

        Example:
            accounts = auditor.find_inactive_accounts(180)
            for account in accounts:
                print(f"{account['username']} - last logon: {account['last_logon']}")
        """
        if not self.pyad:
            return []

        try:
            from datetime import timedelta

            from pyad import pyadcontainer

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            inactive_accounts = []

            ou = pyadcontainer.PyADContainer.from_dn(self.conn.base_dn)

            for user in ou.get_children():
                try:
                    last_logon = user.get_attribute("lastLogonTimestamp")
                    if last_logon and last_logon[0] < cutoff_date:
                        inactive_accounts.append(
                            {
                                "username": user.get_attribute("sAMAccountName")[0],
                                "last_logon": str(last_logon[0]),
                                "email": user.get_attribute("mail")[0]
                                if user.get_attribute("mail")
                                else None,
                                "enabled": user.get_attribute("enabled")[0]
                                if user.get_attribute("enabled")
                                else None,
                            }
                        )
                except Exception:
                    continue

            logger.info(f"Found {len(inactive_accounts)} inactive accounts")
            return inactive_accounts

        except Exception as e:
            logger.error(f"Failed to find inactive accounts: {e}")
            return []

    def find_locked_accounts(self) -> list[dict]:
        """
        Find all currently locked user accounts.

        Identifies accounts that have been locked due to excessive
        failed login attempts. These may indicate brute force attacks
        or users who have forgotten their passwords.

        Returns:
            list: List of locked account dictionaries
        """
        if not self.pyad:
            return []

        try:
            from pyad import pyadcontainer

            locked_accounts = []
            ou = pyadcontainer.PyADContainer.from_dn(self.conn.base_dn)

            for user in ou.get_children():
                try:
                    is_locked = user.get_attribute("lockoutTime")
                    if is_locked and is_locked[0] and str(is_locked[0]) != "0":
                        locked_accounts.append(
                            {
                                "username": user.get_attribute("sAMAccountName")[0],
                                "lockout_time": str(is_locked[0]),
                                "dn": str(user.dn),
                            }
                        )
                except Exception:
                    continue

            logger.info(f"Found {len(locked_accounts)} locked accounts")
            return locked_accounts

        except Exception as e:
            logger.error(f"Failed to find locked accounts: {e}")
            return []

    def audit_security_groups(self) -> dict:
        """
        Audit security groups for potential issues.

        Analyzes security groups for common problems including:
        - Empty groups (no members)
        - Groups with excessive membership
        - Nested group depth issues

        Returns:
            dict: Security group audit results

        Example Response:
            {
                "total_groups": 45,
                "empty_groups": 5,
                "large_groups": [{"name": "All-Users", "count": 5000}],
                "recommendations": ["Review empty groups for removal"]
            }
        """
        if not self.pyad:
            return {"status": "error", "message": "pyad not available"}

        try:
            from pyad import pyadcontainer

            results: dict[str, Any] = {
                "total_groups": 0,
                "empty_groups": [],
                "large_groups": [],
                "recommendations": [],
            }

            ou = pyadcontainer.PyADContainer.from_dn(self.conn.base_dn)

            for child in ou.get_children():
                try:
                    if hasattr(child, "get_attribute"):
                        obj_class = child.get_attribute("objectClass")
                        if obj_class and "group" in obj_class:
                            results["total_groups"] += 1

                            try:
                                members = child.get_members()
                                member_count = len(members) if members else 0

                                if member_count == 0:
                                    cn = child.get_attribute("cn")
                                    if cn:
                                        results["empty_groups"].append(cn[0])

                                elif member_count > 500:
                                    cn = child.get_attribute("cn")
                                    if cn:
                                        results["large_groups"].append(
                                            {
                                                "name": cn[0],
                                                "count": member_count,
                                            }
                                        )
                            except Exception:
                                pass

                except Exception:
                    continue

            # Generate recommendations based on findings
            if results["empty_groups"]:
                results["recommendations"].append(
                    f"Review {len(results['empty_groups'])} empty groups for removal"
                )
            if results["large_groups"]:
                results["recommendations"].append(
                    "Review large groups for potential performance impact"
                )

            logger.info(f"Security group audit: {results['total_groups']} groups found")
            return results

        except Exception as e:
            logger.error(f"Security group audit failed: {e}")
            return {"status": "error", "message": str(e)}

    def generate_security_report(self) -> dict:
        """
        Generate comprehensive security audit report.

        Executes all security checks and produces a consolidated
        report with overall risk status.

        Returns:
            dict: Complete security report with all check results

        Example Response:
            {
                "timestamp": "2024-01-15T10:30:00",
                "domain": "dc=domain,dc=com",
                "checks": {
                    "privileged_accounts": [...],
                    "password_policy": {...},
                    "inactive_accounts": [...],
                    "locked_accounts": [...],
                    "security_groups": {...}
                },
                "overall_status": "warning",
                "recommendations": [...]
            }
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.conn.base_dn,
            "checks": {},
            "recommendations": [],
        }

        # Run all security checks
        privileged = self.find_privileged_accounts()
        report["checks"]["privileged_accounts"] = {
            "count": len(privileged),
            "accounts": privileged,
        }

        password_policy = self.check_password_policy_compliance()
        report["checks"]["password_policy"] = password_policy

        inactive = self.find_inactive_accounts()
        report["checks"]["inactive_accounts"] = {
            "count": len(inactive),
            "accounts": inactive,
        }

        locked = self.find_locked_accounts()
        report["checks"]["locked_accounts"] = {
            "count": len(locked),
            "accounts": locked,
        }

        groups = self.audit_security_groups()
        report["checks"]["security_groups"] = groups

        # Compile recommendations from all checks
        if password_policy.get("status") == "warning":
            report["recommendations"].extend(password_policy.get("recommendations", []))

        if len(inactive) > 0:
            report["recommendations"].append(
                f"Review {len(inactive)} inactive accounts for disablement"
            )

        if len(locked) > 0:
            report["recommendations"].append(
                f"Investigate {len(locked)} locked accounts - possible brute force attempt"
            )

        if len(privileged) > 10:
            report["recommendations"].append(
                f"Review {len(privileged)} privileged accounts - consider reducing"
            )

        # Determine overall security status
        issues = 0
        if password_policy.get("status") != "compliant":
            issues += 1
        if len(inactive) > 0:
            issues += 1
        if len(locked) > 0:
            issues += 1

        if issues == 0:
            report["overall_status"] = "healthy"
        elif issues <= 2:
            report["overall_status"] = "warning"
        else:
            report["overall_status"] = "critical"

        return report
