"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-04-23

"""
import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create initial schema."""
    op.create_table(
        "systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("system_type", sa.String(length=50), nullable=False),
        sa.Column("os", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
    )
    op.create_index("idx_hostname", "systems", ["hostname"])
    op.create_index("idx_status", "systems", ["status"])

    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("schedule", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("last_run", sa.DateTime(), nullable=True),
        sa.Column("next_run", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_job_name", "scheduled_jobs", ["name"])
    op.create_index("idx_enabled", "scheduled_jobs", ["enabled"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_name", sa.String(length=255), nullable=True),
        sa.Column("user", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_timestamp", "audit_logs", ["timestamp"])
    op.create_index("idx_action", "audit_logs", ["action"])
    op.create_index(
        "idx_resource", "audit_logs", ["resource_type", "resource_name"]
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("audit_logs")
    op.drop_table("scheduled_jobs")
    op.drop_table("systems")
