"""Create issues.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("issue_type", sa.Enum("bug", "feature", "task", name="issue_type", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("status", sa.Enum("backlog", "todo", "in_progress", "in_review", "done", "cancelled", name="issue_status", native_enum=False, create_constraint=True), server_default="backlog", nullable=False),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="issue_priority", native_enum=False, create_constraint=True), server_default="medium", nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sprint_id", sa.Integer(), sa.ForeignKey("sprints.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "number", name="uq_issues_project_number"),
        sa.CheckConstraint("number > 0", name="ck_issues_positive_number"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_issues_title_not_blank"),
    )
    op.create_index("ix_issues_project_status", "issues", ["project_id", "status"])
    op.create_index("ix_issues_assignee_id", "issues", ["assignee_id"])
    op.create_index("ix_issues_sprint_id", "issues", ["sprint_id"])


def downgrade() -> None:
    op.drop_index("ix_issues_sprint_id", table_name="issues")
    op.drop_index("ix_issues_assignee_id", table_name="issues")
    op.drop_index("ix_issues_project_status", table_name="issues")
    op.drop_table("issues")
