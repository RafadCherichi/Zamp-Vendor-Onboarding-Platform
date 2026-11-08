"""Add the business activity detail used by the vendor form.

Revision ID: f6b2a4d9c871
Revises: 130ca22502ef
"""

from alembic import op
import sqlalchemy as sa


revision = "f6b2a4d9c871"
down_revision = "130ca22502ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("other_business_activity_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "other_business_activity_description")
