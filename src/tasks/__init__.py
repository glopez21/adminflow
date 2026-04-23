"""AdminFlow Celery tasks."""

from src.tasks.celery import celery_app

__all__ = ["celery_app"]
