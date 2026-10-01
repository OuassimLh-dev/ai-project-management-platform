"""Create issue comments and activity.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issue_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(body)) > 0", name="ck_issue_comments_body_not_blank"),
        sa.CheckConstraint("length(body) <= 10000", name="ck_issue_comments_body_length"),
    )
    op.create_index("ix_issue_comments_issue_id", "issue_comments", ["issue_id"])
    op.create_table(
        "issue_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("field_name", sa.String(30), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("action IN ('created', 'field_changed')", name="ck_issue_activity_action"),
        sa.CheckConstraint("(action = 'created' AND field_name IS NULL AND old_value IS NULL AND new_value IS NULL) OR "
                           "(action = 'field_changed' AND field_name IS NOT NULL AND field_name IN "
                           "('title', 'description', 'issue_type', 'priority', 'status', 'assignee_id', 'sprint_id'))",
                           name="ck_issue_activity_field"),
    )
    op.create_index("ix_issue_activity_issue_id", "issue_activity", ["issue_id"])


def downgrade() -> None:
    op.drop_index("ix_issue_activity_issue_id", table_name="issue_activity")
    op.drop_table("issue_activity")
    op.drop_index("ix_issue_comments_issue_id", table_name="issue_comments")
    op.drop_table("issue_comments")
