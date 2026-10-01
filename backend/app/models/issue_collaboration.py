from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.issue import Issue
from app.models.user import User


class IssueComment(Base):
    __tablename__ = "issue_comments"
    __table_args__ = (
        CheckConstraint("length(trim(body)) > 0", name="ck_issue_comments_body_not_blank"),
        CheckConstraint("length(body) <= 10000", name="ck_issue_comments_body_length"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    issue: Mapped[Issue] = relationship()
    author: Mapped[User] = relationship()


class IssueActivity(Base):
    __tablename__ = "issue_activity"
    __table_args__ = (
        CheckConstraint("action IN ('created', 'field_changed')", name="ck_issue_activity_action"),
        CheckConstraint("(action = 'created' AND field_name IS NULL AND old_value IS NULL AND new_value IS NULL) OR "
                        "(action = 'field_changed' AND field_name IS NOT NULL AND field_name IN "
                        "('title', 'description', 'issue_type', 'priority', 'status', 'assignee_id', 'sprint_id'))",
                        name="ck_issue_activity_field"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    field_name: Mapped[str | None] = mapped_column(String(30))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    issue: Mapped[Issue] = relationship()
    actor: Mapped[User] = relationship()
