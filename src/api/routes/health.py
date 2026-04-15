"""
Health Check API Endpoints for AdminFlow.

This module provides REST API endpoints for monitoring Active Directory
health and status. It supports checking replication, domain controllers,
LDAP connectivity, FSMO roles, and DNS records.

Endpoints:
    GET /api/health/ - Run all AD health checks
    GET /api/health/replication - Check AD replication status
    GET /api/health/domain-controllers - Get list of domain controllers
    GET /api/health/ldap - Test LDAP connectivity
    GET /api/health/fsmo - Check FSMO role holders
    GET /api/health/dns - Verify critical DNS records

Authentication:
    Requires API key or JWT token with appropriate scopes.

Example:
    # Run all health checks
    curl -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/health/

    # Check replication status
    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/health/replication
"""

import logging
from fastapi import APIRouter
from src.utils.ad_connection import ADConnection
from src.health_checks.ad_health import ADHealthChecker
import config.settings as settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_health_checker():
    """
    Create and connect a health checker instance.

    Returns:
        tuple: (ADHealthChecker instance, AD connection)
    """
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    conn.connect()
    return ADHealthChecker(conn), conn


@router.get("/")
async def health_all():
    """
    Run all Active Directory health checks.

    Executes a comprehensive health check covering all aspects of AD
    including replication, LDAP connectivity, domain controllers,
    FSMO role holders, and DNS records.

    Returns:
        dict: Comprehensive health report with overall status

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
    """
    checker, conn = get_health_checker()
    try:
        result = checker.generate_health_report()
        return result
    finally:
        conn.disconnect()


@router.get("/replication")
async def check_replication():
    """
    Check AD replication status between domain controllers.

    Queries the replication status across all domain controllers
    in the domain. Identifies any replication failures or latency
    issues that could indicate problems with AD consistency.

    Returns:
        dict: Replication status and details

    Example Response:
        {
            "status": "healthy",
            "output": "Replication summary...",
            "timestamp": "2024-01-15T10:30:00"
        }
    """
    checker, conn = get_health_checker()
    try:
        result = checker.check_replication()
        return result
    finally:
        conn.disconnect()


@router.get("/domain-controllers")
async def get_domain_controllers():
    """
    Get list of domain controllers in the environment.

    Retrieves all domain controllers and their operational status.
    This includes both primary DC and read-only DCs if present.

    Returns:
        dict: List of domain controllers

    Example Response:
        {
            "controllers": [
                {"name": "DC01.domain.com", "status": "online"},
                {"name": "DC02.domain.com", "status": "online"}
            ]
        }
    """
    checker, conn = get_health_checker()
    try:
        result = checker.check_domain_controllers()
        return {"controllers": result}
    finally:
        conn.disconnect()


@router.get("/ldap")
async def check_ldap(server: str = None):
    """
    Test LDAP connectivity to domain controllers.

    Verifies that LDAP ports (389 for LDAP, 636 for LDAPS) are
    accessible on the specified or default domain controller.

    Args:
        server: Optional specific server to test (defaults to configured AD server)

    Returns:
        dict: LDAP connectivity status

    Example Response:
        {
            "server": "dc01.domain.com",
            "port": 389,
            "status": "accessible",
            "timestamp": "2024-01-15T10:30:00"
        }
    """
    checker, conn = get_health_checker()
    try:
        result = checker.check_ldap_connectivity(server)
        return result
    finally:
        conn.disconnect()


@router.get("/fsmo")
async def check_fsmo():
    """
    Check FSMO (Flexible Single Master Operations) role holders.

    Identifies which domain controller holds each of the five FSMO roles:
    - Schema Master: Schema updates and modifications
    - Domain Naming Master: Domain additions/removals
    - PDC Emulator: Password changes, time sync, GPO processing
    - RID Master: RID pool allocation
    - Infrastructure Master: Cross-domain object references

    Returns:
        dict: FSMO role holders

    Example Response:
        {
            "fsmo_roles": {
                "SchemaMaster": {"status": "found", "holder": "DC01"},
                "DomainNamingMaster": {"status": "found", "holder": "DC01"},
                "PDCEmulator": {"status": "found", "holder": "DC01"},
                "RIDMaster": {"status": "found", "holder": "DC01"},
                "InfrastructureMaster": {"status": "found", "holder": "DC02"}
            }
        }
    """
    checker, conn = get_health_checker()
    try:
        result = checker.check_fsmo_roles()
        return {"fsmo_roles": result}
    finally:
        conn.disconnect()


@router.get("/dns")
async def check_dns():
    """
    Verify critical DNS records for Active Directory.

    Checks for the presence of essential SRV records that AD
    requires for proper operation:
    - _ldap._tcp: LDAP service location
    - _kerberos._tcp: Kerberos authentication
    - _gc._tcp: Global catalog

    Returns:
        dict: DNS record check results

    Example Response:
        {
            "dns_records": {
                "_ldap._tcp": {"status": "found", "servers": ["192.168.1.10"]},
                "_kerberos._tcp": {"status": "found", "servers": ["192.168.1.10"]},
                "_gc._tcp": {"status": "found", "servers": ["192.168.1.10"]}
            }
        }
    """
    checker, conn = get_health_checker()
    try:
        result = checker.check_dns_records()
        return {"dns_records": result}
    finally:
        conn.disconnect()
