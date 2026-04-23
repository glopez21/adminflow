"""CRUD service for database models."""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models import AuditLog, ScheduledJob, System


class SystemService:
    """CRUD operations for systems."""

    @staticmethod
    def create_system(
        db: Session,
        hostname: str,
        ip_address: str,
        system_type: str,
        os: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> System:
        """Create a new system in the inventory."""
        system = System(
            hostname=hostname,
            ip_address=ip_address,
            system_type=system_type,
            os=os,
            description=description,
            location=location,
            tags=tags,
        )
        db.add(system)
        db.commit()
        db.refresh(system)
        return system

    @staticmethod
    def get_system(db: Session, system_id: int) -> Optional[System]:
        """Get system by ID."""
        return db.query(System).filter(System.id == system_id).first()

    @staticmethod
    def get_system_by_hostname(db: Session, hostname: str) -> Optional[System]:
        """Get system by hostname."""
        return db.query(System).filter(System.hostname == hostname).first()

    @staticmethod
    def list_systems(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[System]:
        """List systems with optional filtering."""
        query = db.query(System)
        if status:
            query = query.filter(System.status == status)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_system(
        db: Session,
        system_id: int,
        **kwargs,
    ) -> Optional[System]:
        """Update system attributes."""
        system = db.query(System).filter(System.id == system_id).first()
        if system:
            for key, value in kwargs.items():
                if hasattr(system, key) and value is not None:
                    setattr(system, key, value)
            db.commit()
            db.refresh(system)
        return system

    @staticmethod
    def delete_system(db: Session, system_id: int) -> bool:
        """Delete a system."""
        system = db.query(System).filter(System.id == system_id).first()
        if system:
            db.delete(system)
            db.commit()
            return True
        return False


class JobService:
    """CRUD operations for scheduled jobs."""

    @staticmethod
    def create_job(
        db: Session,
        name: str,
        job_type: str,
        schedule: str,
    ) -> ScheduledJob:
        """Create a new scheduled job."""
        job = ScheduledJob(
            name=name,
            job_type=job_type,
            schedule=schedule,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: int) -> Optional[ScheduledJob]:
        """Get job by ID."""
        return db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    @staticmethod
    def list_jobs(db: Session, enabled: Optional[bool] = None) -> List[ScheduledJob]:
        """List jobs with optional filtering."""
        query = db.query(ScheduledJob)
        if enabled is not None:
            query = query.filter(ScheduledJob.enabled == enabled)
        return query.all()

    @staticmethod
    def update_job(
        db: Session,
        job_id: int,
        **kwargs,
    ) -> Optional[ScheduledJob]:
        """Update job attributes."""
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if job:
            for key, value in kwargs.items():
                if hasattr(job, key) and value is not None:
                    setattr(job, key, value)
            db.commit()
            db.refresh(job)
        return job


class AuditService:
    """CRUD operations for audit logs."""

    @staticmethod
    def create_log(
        db: Session,
        action: str,
        resource_type: str,
        resource_name: Optional[str] = None,
        user: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_name=resource_name,
            user=user,
            status=status,
            details=details,
            ip_address=ip_address,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """List audit logs with optional filtering."""
        query = db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
