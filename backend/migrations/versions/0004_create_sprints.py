"""Create sprints.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("planned", "active", "completed", "cancelled", name="sprint_status",
                                    native_enum=False, create_constraint=True), server_default="planned", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_sprints_name_not_blank"),
        sa.CheckConstraint("end_date >= start_date", name="ck_sprints_date_order"),
    )
    op.create_index("ix_sprints_project_id", "sprints", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_sprints_project_id", table_name="sprints")
    op.drop_table("sprints")
