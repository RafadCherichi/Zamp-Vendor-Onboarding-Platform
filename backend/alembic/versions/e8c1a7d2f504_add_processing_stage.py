"""Record the actual document processing stage.

Revision ID: e8c1a7d2f504
Revises: f6b2a4d9c871
"""

from alembic import op
import sqlalchemy as sa


revision = "e8c1a7d2f504"
down_revision = "f6b2a4d9c871"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_processing_jobs", sa.Column("stage", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("document_processing_jobs", "stage")
