"""Create AI analyses.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("suggested_type", sa.Enum("bug", "feature", "task", name="ai_suggested_type", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("suggested_priority", sa.Enum("low", "medium", "high", "critical", name="ai_suggested_priority", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(summary)) > 0 AND length(summary) <= 2000", name="ck_ai_analyses_summary"),
        sa.CheckConstraint("length(trim(explanation)) > 0 AND length(explanation) <= 1000", name="ck_ai_analyses_explanation"),
        sa.CheckConstraint("length(trim(model_name)) > 0 AND length(model_name) <= 200", name="ck_ai_analyses_model_name"),
    )
    op.create_index("ix_ai_analyses_issue_id", "ai_analyses", ["issue_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_analyses_issue_id", table_name="ai_analyses")
    op.drop_table("ai_analyses")
