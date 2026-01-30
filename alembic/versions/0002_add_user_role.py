"""add user role

Revision ID: 0002_add_user_role
Revises: 0001_initial
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_user_role"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="member"),
    )
    op.execute("""
        UPDATE users u
        SET role = 'admin'
        FROM (
            SELECT company_id, MIN(created_at) AS min_created
            FROM users
            GROUP BY company_id
        ) first_users
        WHERE u.company_id = first_users.company_id
          AND u.created_at = first_users.min_created
    """)
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")


def downgrade():
    op.drop_column("users", "role")
