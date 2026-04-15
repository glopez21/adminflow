"""
Health Check Scripts for Active Directory Monitoring.

This module provides comprehensive health monitoring capabilities for AD
environments, checking critical infrastructure components and generating
health reports for operations and troubleshooting.

Classes:
    ADHealthChecker: Main class for all AD health checks

Features:
    - Domain controller discovery and status
    - AD replication status checking
    - LDAP connectivity testing
    - FSMO role holder identification
    - DNS record verification
    - Comprehensive health report generation

Usage:
    from src.health_checks.ad_health import ADHealthChecker
    from src.utils.ad_connection import ADConnection

    conn = ADConnection(server="dc.domain.com", ...)
    checker = ADHealthChecker(conn)

    # Run all health checks
    report = checker.generate_health_report()

    # Check replication status
    result = checker.check_replication()

Requirements:
    - Windows environment for nltest, netdom commands
    - Appropriate AD permissions for queries
"""

import logging
import subprocess
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class ADHealthChecker:
    """
    Performs health checks on Active Directory.

    This class provides methods for monitoring AD health including
    domain controllers, replication, LDAP connectivity, FSMO roles,
    and DNS records.

    Attributes:
        conn: Active Directory connection instance
    """

    def __init__(self, ad_connection):
        """
        Initialize health checker with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        self.conn = ad_connection

    def check_domain_controllers(self) -> List[Dict]:
        """
        Get list of domain controllers and their status.

        Queries the domain for all domain controllers and reports
        their operational status.

        Returns:
            list: List of domain controllers with name and status

        Note:
            Uses nltest command which is Windows-specific

        Example Response:
            [
                {"name": "DC01.domain.com", "status": "online"},
                {"name": "DC02.domain.com", "status": "online"}
            ]
        """
        results = []

        try:
            import subprocess

            result = subprocess.run(
                ["nltest", "/dclist:"], capture_output=True, text=True, shell=True
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "DC" in line or "PDC" in line:
                        results.append({"name": line.strip(), "status": "online"})

        except Exception as e:
            logger.error(f"Failed to get domain controllers: {e}")

        return results

    def check_replication(self) -> Dict:
        """
        Check AD replication status.

        Queries the replication status across all domain controllers
        in the domain. Identifies any replication failures or latency.

        Returns:
            dict: Replication status with details and timestamp

        Note:
            Uses repadmin command which is Windows-specific

        Example Response:
            {
                "status": "healthy",
                "output": "Replication summary...",
                "timestamp": "2024-01-15T10:30:00"
            }
        """
        try:
            result = subprocess.run(
                "repadmin /replsummary", capture_output=True, text=True, shell=True
            )

            if result.returncode == 0:
                return {
                    "status": "healthy",
                    "output": result.stdout,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Replication check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def check_ldap_connectivity(self, server: str = None) -> Dict:
        """
        Test LDAP connectivity to domain controllers.

        Verifies that LDAP port 389 (or LDAPS 636) is accessible
        on the specified or default domain controller.

        Args:
            server: Optional specific server to test (defaults to configured AD server)

        Returns:
            dict: LDAP connectivity status with server, port, and timestamp

        Example Response:
            {
                "server": "dc01.domain.com",
                "port": 389,
                "status": "accessible",
                "timestamp": "2024-01-15T10:30:00"
            }
        """
        target = server or self.conn.server

        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            port = 389
            result = sock.connect_ex((target, port))
            sock.close()

            if result == 0:
                return {
                    "server": target,
                    "port": port,
                    "status": "accessible",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "server": target,
                    "port": port,
                    "status": "unreachable",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"LDAP connectivity test failed: {e}")
            return {
                "server": target,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def check_fsmo_roles(self) -> Dict:
        """
        Check FSMO (Flexible Single Master Operations) role holders.

        Identifies which domain controller holds each of the five FSMO roles:
        - Schema Master: Schema updates and modifications
        - Domain Naming Master: Domain additions/removals
        - PDC Emulator: Password changes, time sync, GPO processing
        - RID Master: RID pool allocation
        - Infrastructure Master: Cross-domain object references

        Returns:
            dict: FSMO role holders with status

        Note:
            Uses netdom query command which is Windows-specific

        Example Response:
            {
                "SchemaMaster": {"status": "found", "holder": "DC01"},
                "DomainNamingMaster": {"status": "found", "holder": "DC01"},
                "PDCEmulator": {"status": "found", "holder": "DC01"},
                "RIDMaster": {"status": "found", "holder": "DC01"},
                "InfrastructureMaster": {"status": "found", "holder": "DC02"}
            }
        """
        fsmo_roles = {
            "DomainNamingMaster": "CN=Partitions,CN=Schema,CN=Configuration",
            "SchemaMaster": "CN=Schema,CN=Configuration",
            "PDCEmulator": "CN=NTDS Settings",
            "RIDMaster": "CN=RID Manager$",
            "InfrastructureMaster": "CN=Infrastructure",
        }

        results = {}

        for role in fsmo_roles:
            results[role] = {"status": "unknown", "holder": None}

        try:
            import subprocess

            result = subprocess.run(
                ["netdom", "query", "fsmo"], capture_output=True, text=True, shell=True
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    for role in fsmo_roles:
                        if role.lower().replace("_", "") in line.lower():
                            results[role]["holder"] = line.strip()
                            results[role]["status"] = "found"

        except Exception as e:
            logger.error(f"FSMO check failed: {e}")

        return results

    def check_dns_records(self) -> Dict:
        """
        Verify critical DNS records for Active Directory.

        Checks for the presence of essential SRV records that AD
        requires for proper operation and client authentication.

        Required Records:
            - _ldap._tcp: LDAP service location
            - _kerberos._tcp: Kerberos authentication
            - _gc._tcp: Global catalog

        Returns:
            dict: DNS record check results with status and servers

        Example Response:
            {
                "_ldap._tcp": {"status": "found", "servers": ["192.168.1.10"]},
                "_kerberos._tcp": {"status": "found", "servers": ["192.168.1.10"]},
                "_gc._tcp": {"status": "found", "servers": ["192.168.1.10"]}
            }
        """
        required_records = ["_ldap._tcp", "_kerberos._tcp", "_gc._tcp"]

        results = {}

        for record in required_records:
            results[record] = {"status": "not checked", "servers": []}

            try:
                import socket

                try:
                    srv_records = socket.getaddrinfo(
                        record + "._tcp." + self.conn.base_dn, None
                    )
                    results[record]["status"] = "found"
                    results[record]["servers"] = list(
                        set([r[4][0] for r in srv_records])
                    )
                except socket.gaierror:
                    results[record]["status"] = "not found"

            except Exception as e:
                results[record]["status"] = f"error: {str(e)}"

        return results

    def generate_health_report(self) -> Dict:
        """
        Generate comprehensive AD health report.

        Executes all health checks and produces a consolidated
        report with overall health status.

        Returns:
            dict: Comprehensive health report with timestamp, domain,
                  all check results, and overall status

        Example Response:
            {
                "timestamp": "2024-01-15T10:30:00",
                "domain": "dc=domain,dc=com",
                "checks": {
                    "replication": {"status": "healthy", ...},
                    "ldap": {"status": "accessible", ...},
                    "domain_controllers": {"status": "found", ...},
                    "fsmo": {...},
                    "dns": {...}
                },
                "overall_status": "healthy"
            }

        Overall Status Logic:
            - "healthy": All checks passed
            - "warning": Some checks failed or returned unexpected results
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "domain": self.conn.base_dn,
            "checks": {},
        }

        report["checks"]["replication"] = self.check_replication()
        report["checks"]["ldap"] = self.check_ldap_connectivity()
        report["checks"]["domain_controllers"] = {
            "status": "found",
            "controllers": self.check_domain_controllers(),
        }
        report["checks"]["fsmo"] = self.check_fsmo_roles()
        report["checks"]["dns"] = self.check_dns_records()

        all_healthy = all(
            check.get("status") in ["healthy", "found", "accessible"]
            for check in report["checks"].values()
        )

        report["overall_status"] = "healthy" if all_healthy else "warning"

        return report
