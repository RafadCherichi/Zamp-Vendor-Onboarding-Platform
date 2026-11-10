"""Store vendor corrections separately from original OCR output.

Revision ID: 9c3a72ef1b04
Revises: f6b2a4d9c871
"""

from alembic import op
import sqlalchemy as sa


revision = "9c3a72ef1b04"
down_revision = "f6b2a4d9c871"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("extracted_fields", schema=None) as batch_op:
        batch_op.add_column(sa.Column("vendor_corrected_value", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("vendor_correction_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("vendor_corrected_by_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("vendor_corrected_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_extracted_fields_vendor_corrected_by_user_id_users",
            "users",
            ["vendor_corrected_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("extracted_fields", schema=None) as batch_op:
        batch_op.drop_constraint("fk_extracted_fields_vendor_corrected_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("vendor_corrected_at")
        batch_op.drop_column("vendor_corrected_by_user_id")
        batch_op.drop_column("vendor_correction_reason")
        batch_op.drop_column("vendor_corrected_value")
