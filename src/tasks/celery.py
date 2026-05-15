"""Celery configuration and tasks."""

import logging
import os
from typing import Any

from celery import Celery

from src.utils.azure_ad import create_azure_manager_from_config

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "adminflow",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


_celery_pool: Any = None


def _get_pool() -> Any:
    global _celery_pool
    if _celery_pool is None:
        from src.utils.ad_connection import ADConnectionPool
        _celery_pool = ADConnectionPool(max_size=5, ttl_seconds=600)
    return _celery_pool


def _pooled_conn():
    """Create a pooled AD connection from environment variables."""
    from src.utils.ad_connection import get_pooled_connection

    return get_pooled_connection(
        server=os.getenv("AD_SERVER", "dc01.local"),
        username=os.getenv("AD_USER", "admin@local"),
        password=os.getenv("AD_PASSWORD", ""),
        base_dn=os.getenv("AD_BASE_DN", "dc=local"),
        pool=_get_pool(),
    )


@celery_app.task(bind=True, name="adminflow.tasks.health_check")
def run_health_check(self, check_type: str = "all") -> dict:
    """Run AD health check task."""
    try:
        from src.health_checks.ad_health import ADHealthChecker

        conn = _pooled_conn()

        check_type_map = {
            "all": "generate_health_report",
            "replication": "check_replication",
            "dc": "check_domain_controllers",
            "ldap": "check_ldap_connectivity",
            "fsmo": "check_fsmo_roles",
        }
        checker = ADHealthChecker(conn)
        method = getattr(checker, check_type_map.get(check_type, "generate_health_report"))
        result = method()
        _get_pool().release(conn)

        return {"status": "success", "checks": result}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="adminflow.tasks.security_audit")
def run_security_audit(self, audit_type: str = "all") -> dict:
    """Run security audit task."""
    try:
        from src.security.ad_security import ADSecurityAuditor

        conn = _pooled_conn()

        audit_type_map = {
            "all": "generate_security_report",
            "privileged": "find_privileged_accounts",
            "password": "check_password_policy_compliance",
            "inactive": "find_inactive_accounts",
            "locked": "find_locked_accounts",
        }
        auditor = ADSecurityAuditor(conn)
        method = getattr(auditor, audit_type_map.get(audit_type, "generate_security_report"))
        result = method()
        _get_pool().release(conn)

        return {"status": "success", "audits": result}
    except Exception as e:
        logger.error(f"Security audit failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="adminflow.tasks.find_inactive_users")
def find_inactive_users(self, days: int = 90) -> dict:
    """Find inactive users task."""
    try:
        from src.user_management.ad_user_manager import ADUserManager

        conn = _pooled_conn()

        manager = ADUserManager(conn)
        result = manager.find_inactive_users(days)
        _get_pool().release(conn)

        return {"status": "success", "inactive_users": result}
    except Exception as e:
        logger.error(f"Find inactive users failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="adminflow.tasks.azure_sync")
def sync_azure_ad(self) -> dict:
    """Sync with Azure AD."""
    try:
        azure = create_azure_manager_from_config()
        if azure is None:
            return {"status": "error", "message": "Azure AD not configured"}
        users = azure.list_users()
        return {"status": "success", "user_count": len(users)}
    except Exception as e:
        logger.error(f"Azure sync failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="adminflow.tasks.network_scan")
def run_network_scan(
    self,
    network_range: str,
    scan_types: list,
) -> dict:
    """Run network scan task."""
    try:
        from src.utils.network import scan_network

        result = scan_network(network_range, scan_types)
        return {"status": "success", "results": result}
    except Exception as e:
        logger.error(f"Network scan failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="adminflow.tasks.backup_config")
def backup_configuration(self) -> dict:
    """Backup configuration task."""
    try:
        import json
        from datetime import datetime, timezone

        config = {
            "ad_server": os.getenv("AD_SERVER"),
            "ad_base_dn": os.getenv("AD_BASE_DN"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        backup_file = f"config_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, "w") as f:
            json.dump(config, f, indent=2)

        return {"status": "success", "backup_file": backup_file}
    except Exception as e:
        logger.error(f"Config backup failed: {e}")
        return {"status": "error", "message": str(e)}


celery_app.conf.beat_schedule = {
    "daily-health-check": {
        "task": "adminflow.tasks.health_check",
        "schedule": 21600.0,
        "args": ("all",),
    },
    "weekly-security-audit": {
        "task": "adminflow.tasks.security_audit",
        "schedule": 604800.0,
        "args": ("all",),
    },
    "daily-inactive-check": {
        "task": "adminflow.tasks.find_inactive_users",
        "schedule": 86400.0,
        "args": (90,),
    },
    "daily-config-backup": {
        "task": "adminflow.tasks.backup_config",
        "schedule": 86400.0,
        "args": (),
    },
}
