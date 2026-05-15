"""
Scheduled Automation Jobs for Active Directory Management.

This module provides a scheduling system for automating recurring AD management
tasks such as health checks, security audits, inactive account reporting,
and configuration backups. It uses APScheduler for background job scheduling.

Classes:
    AutomationJob: Base class for all scheduled jobs
    HealthCheckJob: Daily AD health check job
    InactiveAccountsJob: Weekly inactive accounts report
    SecurityAuditJob: Weekly security audit job
    BackupConfigJob: Daily configuration backup job
    SchedulerManager: Manager for scheduling and running jobs

Features:
    - Cron-based and interval-based scheduling
    - Job status tracking and manual triggering
    - Automatic report generation and file storage
    - Comprehensive error handling and logging

Usage:
    from src.utils.scheduler import SchedulerManager, create_default_schedule
    from src.utils.ad_connection import ADConnection
    import config.settings as settings

    conn = ADConnection(server=settings.AD_SERVER, ...)
    conn.connect()

    scheduler = SchedulerManager(conn)
    create_default_schedule(scheduler)
    scheduler.start()

    # Trigger a job manually
    result = scheduler.run_job_now("ad_health_check")

    # Get scheduled job info
    next_runs = scheduler.get_next_runs()

Requirements:
    - apscheduler: For background job scheduling
"""

import json
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class AutomationJob:
    """
    Base class for all scheduled automation jobs.

    Provides common functionality for job tracking, status reporting,
    and timestamp management. All scheduled jobs should inherit from
    this class and implement the run() method.

    Attributes:
        name: Unique job identifier/name
        description: Human-readable description of the job
        last_run: Timestamp of the last successful execution
        last_result: Result dictionary from the last execution
        enabled: Whether the job is active

    Example:
        class MyJob(AutomationJob):
            def __init__(self):
                super().__init__("my_job", "My custom job")

    def run(self) -> dict:
                # Do work here
                return {"status": "success"}
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize automation job with name and description.

        Args:
            name: Unique identifier for the job
            description: Human-readable description
        """
        self.name = name
        self.description = description
        self.last_run: datetime | None = None
        self.last_result: dict | None = None
        self.enabled = True

    def run(self) -> dict:
        raise NotImplementedError

    def to_dict(self) -> dict:
        """
        Convert job to dictionary for status reporting.

        Returns:
            dict: Job information including name, description,
                  last run time, and enabled status
        """
        return {
            "name": self.name,
            "description": self.description,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "enabled": self.enabled,
        }


class HealthCheckJob(AutomationJob):
    """
    Daily AD health check job.

    Runs a comprehensive Active Directory health check including
    replication status, domain controller availability, LDAP
    connectivity, FSMO role verification, and DNS record checks.
    Results are saved to a JSON report file.

    Attributes:
        ad_conn: Active Directory connection for health checks

    Example:
        conn = ADConnection(server="dc.domain.com", ...)
        job = HealthCheckJob(conn)
        result = job.run()
    """

    def __init__(self, ad_connection):
        """
        Initialize health check job with AD connection.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        super().__init__("ad_health_check", "Daily AD health check")
        self.ad_conn = ad_connection

    def run(self) -> dict:
        from src.health_checks.ad_health import ADHealthChecker

        checker = ADHealthChecker(self.ad_conn)
        result = checker.generate_health_report()

        self.last_run = datetime.now(timezone.utc)
        self.last_result = result

        self._save_report(result)

        return result

    def _save_report(self, result: dict):
        """
        Save health check report to JSON file.

        Creates the reports directory if needed and writes the
        health check results to a timestamped JSON file.

        Args:
            result: Health check results dictionary
        """
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename = f"health_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        with open(f"{reports_dir}/{filename}", "w") as f:
            json.dump(result, f, indent=2)

        logger.info(f"Health report saved to {reports_dir}/{filename}")


class InactiveAccountsJob(AutomationJob):
    """
    Weekly inactive accounts report job.

    Identifies user accounts that have been inactive for longer than
    a specified threshold. Useful for security hygiene and compliance
    reporting.

    Attributes:
        ad_conn: Active Directory connection
        threshold_days: Number of days of inactivity to flag (default: 90)
    """

    def __init__(self, ad_connection, threshold_days: int = 90):
        """
        Initialize inactive accounts job.

        Args:
            ad_connection: ADConnection instance for AD operations
            threshold_days: Days of inactivity threshold (default: 90)
        """
        super().__init__(
            "inactive_accounts", f"Find accounts inactive for {threshold_days} days"
        )
        self.ad_conn = ad_connection
        self.threshold_days = threshold_days

    def run(self) -> dict:
        from src.security.ad_security import ADSecurityAuditor

        auditor = ADSecurityAuditor(self.ad_conn)
        result = auditor.find_inactive_accounts(self.threshold_days)

        self.last_run = datetime.now(timezone.utc)

        self._save_report(result)

        return {"found": len(result), "accounts": result}

    def _save_report(self, result: list[dict]):
        """
        Save inactive accounts report to JSON file.

        Args:
            result: List of inactive account dictionaries
        """
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename = f"inactive_accounts_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        with open(f"{reports_dir}/{filename}", "w") as f:
            json.dump(result, f, indent=2)


class SecurityAuditJob(AutomationJob):
    """
    Weekly security audit job.

    Runs a comprehensive security audit of the Active Directory
    environment including privileged accounts, password policy,
    group auditing, and account lockout checks.

    Attributes:
        ad_conn: Active Directory connection
    """

    def __init__(self, ad_connection):
        """
        Initialize security audit job.

        Args:
            ad_connection: ADConnection instance for AD operations
        """
        super().__init__("security_audit", "Weekly security audit")
        self.ad_conn = ad_connection

    def run(self) -> dict:
        from src.security.ad_security import ADSecurityAuditor

        auditor = ADSecurityAuditor(self.ad_conn)
        result = auditor.generate_security_report()

        self.last_run = datetime.now(timezone.utc)

        self._save_report(result)

        return result

    def _save_report(self, result: dict):
        """
        Save security audit report to JSON file.

        Args:
            result: Security audit results dictionary
        """
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename = f"security_audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        with open(f"{reports_dir}/{filename}", "w") as f:
            json.dump(result, f, indent=2)


class BackupConfigJob(AutomationJob):
    """
    Daily configuration backup job.

    Creates a compressed archive of the configuration directory
    for backup and disaster recovery purposes.

    Attributes:
        config_dir: Path to the configuration directory to back up
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize backup configuration job.

        Args:
            config_dir: Path to config directory (default: "config")
        """
        super().__init__("config_backup", "Backup configuration files")
        self.config_dir = config_dir

    def run(self) -> dict:
        """
        Execute configuration backup.

        Creates a tar.gz archive of the configuration directory
        with a timestamp in the filename.

        Returns:
            dict: Backup status and file path, or error details
        """
        import tarfile

        backup_dir = "reports/backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/config_backup_{timestamp}.tar.gz"

        try:
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.config_dir, arcname="config")

            self.last_run = datetime.now(timezone.utc)

            return {"status": "success", "backup_file": backup_file}
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"status": "error", "error": str(e)}


class SchedulerManager:
    """
    Manages all scheduled automation jobs.

    Provides a unified interface for adding, removing, triggering,
    and monitoring scheduled AD automation jobs using APScheduler.

    Attributes:
        scheduler: APScheduler BackgroundScheduler instance
        jobs: Dictionary mapping job names to AutomationJob instances
        ad_conn: Active Directory connection (optional)

    Example:
        manager = SchedulerManager(ad_connection)
        manager.add_job(HealthCheckJob(ad_connection), "cron", hour=6)
        manager.start()

        # Check next run times
        next_runs = manager.get_next_runs()

        # Manually trigger a job
        result = manager.run_job_now("ad_health_check")
    """

    def __init__(self, ad_connection=None):
        """
        Initialize the scheduler manager.

        Args:
            ad_connection: Optional ADConnection for AD-related jobs
        """
        self.scheduler = BackgroundScheduler()
        self.jobs: dict[str, AutomationJob] = {}
        self.ad_conn = ad_connection

    def add_job(self, job: AutomationJob, trigger_type: str = "cron", **trigger_args):
        """
        Add a job to the scheduler.

        Registers a job with the scheduler using either cron-based or
        interval-based scheduling.

        Args:
            job: AutomationJob instance to schedule
            trigger_type: Type of trigger - "cron" for time-based or "interval" for periodic
            **trigger_args: Arguments for the trigger type

        Trigger Examples:
            # Cron trigger - every day at 6:00 AM
            add_job(job, "cron", hour=6, minute=0)

            # Cron trigger - every Sunday at 2:00 AM
            add_job(job, "cron", day_of_week="sun", hour=2, minute=0)

            # Interval trigger - every 24 hours
            add_job(job, "interval", hours=24)

        Raises:
            ValueError: If trigger_type is not "cron" or "interval"
        """
        self.jobs[job.name] = job

        if trigger_type == "cron":
            trigger = CronTrigger(**trigger_args)
        elif trigger_type == "interval":
            trigger = IntervalTrigger(**trigger_args)
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

        self.scheduler.add_job(job.run, trigger, id=job.name, replace_existing=True)

        logger.info(f"Added job: {job.name} with {trigger_type} trigger")

    def remove_job(self, job_name: str):
        """
        Remove a job from the scheduler.

        Args:
            job_name: Name of the job to remove
        """
        if job_name in self.jobs:
            self.scheduler.remove_job(job_name)
            del self.jobs[job_name]
            logger.info(f"Removed job: {job_name}")

    def start(self):
        """
        Start the scheduler.

        Begins executing scheduled jobs according to their triggers.
        Only starts if the scheduler is not already running.
        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        """
        Stop the scheduler.

        Gracefully shuts down the scheduler, allowing running
        jobs to complete.
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def get_jobs(self) -> list[dict]:
        """
        Get status of all registered jobs.

        Returns:
            list: List of job status dictionaries
        """
        return [job.to_dict() for job in self.jobs.values()]

    def run_job_now(self, job_name: str) -> dict:
        """
        Manually trigger a job to run immediately.

        Executes the specified job outside of its normal schedule
        and returns the result.

        Args:
            job_name: Name of the job to trigger

        Returns:
            dict: Job execution result or error message
        """
        if job_name not in self.jobs:
            return {"status": "error", "message": f"Job {job_name} not found"}

        try:
            result = self.jobs[job_name].run()
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Job {job_name} failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_next_runs(self) -> dict:
        """
        Get next scheduled run times for all jobs.

        Returns:
            dict: Mapping of job names to their next run time strings
        """
        jobs = self.scheduler.get_jobs()
        return {
            job.id: str(job.next_run_time) if job.next_run_time else None
            for job in jobs
        }


def create_default_schedule(scheduler: SchedulerManager):
    """
    Create default job schedule with recommended frequencies.

    Sets up the standard automation schedule:
    - Health check: Daily at 6:00 AM
    - Security audit: Weekly on Sunday at 2:00 AM
    - Inactive accounts: Weekly on Monday at 7:00 AM
    - Config backup: Every 24 hours

    Args:
        scheduler: SchedulerManager instance to add jobs to

    Example:
        scheduler = SchedulerManager(ad_connection)
        create_default_schedule(scheduler)
        scheduler.start()
    """
    scheduler.add_job(
        HealthCheckJob(scheduler.ad_conn), trigger_type="cron", hour=6, minute=0
    )

    scheduler.add_job(
        SecurityAuditJob(scheduler.ad_conn),
        trigger_type="cron",
        day_of_week="sunday",
        hour=2,
        minute=0,
    )

    scheduler.add_job(
        InactiveAccountsJob(scheduler.ad_conn),
        trigger_type="cron",
        day_of_week="monday",
        hour=7,
        minute=0,
    )

    scheduler.add_job(BackupConfigJob(), trigger_type="interval", hours=24)
