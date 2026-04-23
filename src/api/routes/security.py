"""
Security Audit API Endpoints for AdminFlow.

This module provides REST API endpoints for security auditing and monitoring
of the Active Directory environment. It supports finding privileged accounts,
checking password policies, identifying inactive/locked accounts, and
performing network scans.

Endpoints:
    GET /api/security/ - Run all security audits
    GET /api/security/privileged - Find privileged accounts
    GET /api/security/password-policy - Check password policy settings
    GET /api/security/inactive/{days} - Find inactive accounts
    GET /api/security/locked - Find locked accounts
    GET /api/security/groups - Audit security groups
    POST /api/security/network-scan - Scan network for devices
    POST /api/security/health-check - Perform health check on target

Authentication:
    Requires API key or JWT token with appropriate scopes.

Example:
    # Get all privileged accounts
    curl -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/security/privileged

    # Run all security audits
    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/security/
"""

import logging

from fastapi import APIRouter

import config.settings as settings
from src.api.models.schemas import HealthCheckRequest, NetworkScanRequest
from src.security.ad_security import ADSecurityAuditor
from src.utils.ad_connection import ADConnection

logger = logging.getLogger(__name__)
router = APIRouter()


def get_security_auditor():
    """
    Create and connect a security auditor instance.

    Returns:
        tuple: (ADSecurityAuditor instance, AD connection)
    """
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    conn.connect()
    return ADSecurityAuditor(conn), conn


@router.get("/")
async def security_all():
    """
    Run all security audits and generate comprehensive report.

    Executes all security audit checks including privileged accounts,
    password policy compliance, inactive accounts, locked accounts,
    and security group analysis.

    Returns:
        dict: Comprehensive security audit report with findings
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.generate_security_report()
        return result
    finally:
        conn.disconnect()


@router.get("/privileged")
async def get_privileged_accounts():
    """
    Find all privileged accounts in Active Directory.

    Identifies accounts that are members of privileged groups such as
    Domain Admins, Enterprise Admins, Schema Admins, etc. These
    accounts require special monitoring and regular access reviews.

    Returns:
        dict: Count and list of privileged accounts with their groups

    Example Response:
        {
            "count": 5,
            "accounts": [
                {"username": "admin", "group": "Domain Admins"},
                {"username": "service_account", "group": "Schema Admins"}
            ]
        }
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.find_privileged_accounts()
        return {"count": len(result), "accounts": result}
    finally:
        conn.disconnect()


@router.get("/password-policy")
async def check_password_policy():
    """
    Check password policy settings and compliance.

    Analyzes the domain's password policy settings including minimum
    password length, password complexity requirements, maximum password
    age, and lockout thresholds.

    Returns:
        dict: Password policy configuration and compliance status
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.check_password_policy_compliance()
        return result
    finally:
        conn.disconnect()


@router.get("/inactive/{days}")
async def get_inactive_accounts(days: int = 90):
    """
    Find accounts that haven't logged in for specified days.

    Identifies user accounts that have been inactive beyond the
    specified threshold. These accounts may be candidates for
    disablement or removal to reduce security exposure.

    Args:
        days: Number of days of inactivity threshold (default: 90)

    Returns:
        dict: Count and list of inactive accounts

    Example:
        GET /api/security/inactive/180 - Find accounts inactive for 6 months
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.find_inactive_accounts(days)
        return {"count": len(result), "accounts": result}
    finally:
        conn.disconnect()


@router.get("/locked")
async def get_locked_accounts():
    """
    Find all currently locked user accounts.

    Identifies accounts that are locked due to multiple failed
    login attempts. May indicate brute force attack attempts.

    Returns:
        dict: Count and list of locked accounts
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.find_locked_accounts()
        return {"count": len(result), "accounts": result}
    finally:
        conn.disconnect()


@router.get("/groups")
async def audit_security_groups():
    """
    Audit security groups in Active Directory.

    Analyzes security groups for potential issues including
    nested group memberships, empty groups, and overly
    permissive group memberships.

    Returns:
        dict: Security group audit results
    """
    auditor, conn = get_security_auditor()
    try:
        result = auditor.audit_security_groups()
        return result
    finally:
        conn.disconnect()


@router.post("/network-scan")
async def network_scan(request: NetworkScanRequest):
    """
    Scan network for active devices and services.

    Performs a network scan to discover active hosts and open ports.
    Uses concurrent scanning for efficient coverage of large networks.

    Args:
        request: NetworkScanRequest with scan parameters

    Returns:
        dict: Scan results with discovered hosts and services

    Example:
        POST /api/security/network-scan
        {
            "network_range": "192.168.1.0/24",
            "scan_types": ["ping", "port"],
            "ports": [22, 80, 443, 3389]
        }
    """
    from src.api.routes import systems as sys_module

    result = sys_module.scan_network(
        network_range=request.network_range,
        scan_types=request.scan_types,
        ports=request.ports,
    )
    return result


@router.post("/health-check")
async def health_check(request: HealthCheckRequest):
    """
    Perform health check on a specific target.

    Tests connectivity and availability of a specific host using
    various check types (ping, port, service, url).

    Args:
        request: HealthCheckRequest with check parameters

    Returns:
        dict: Health check results

    Example:
        POST /api/security/health-check
        {
            "target": "dc01.domain.com",
            "check_type": "port",
            "port": 389,
            "timeout": 10
        }
    """
    from src.api.routes import systems as sys_module

    result = sys_module.check_target(
        target=request.target,
        check_type=request.check_type,
        port=request.port,
        timeout=request.timeout,
    )
    return result
