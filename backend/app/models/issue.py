from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLAlchemyEnum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.user import User


class IssueType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"


class IssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


def enum_type(enum, name):
    return SQLAlchemyEnum(enum, values_callable=lambda values: [value.value for value in values],
                          native_enum=False, create_constraint=True, validate_strings=True, name=name)


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_issues_project_number"),
        CheckConstraint("number > 0", name="ck_issues_positive_number"),
        CheckConstraint("length(trim(title)) > 0", name="ck_issues_title_not_blank"),
        Index("ix_issues_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    number: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    issue_type: Mapped[IssueType] = mapped_column(enum_type(IssueType, "issue_type"))
    status: Mapped[IssueStatus] = mapped_column(enum_type(IssueStatus, "issue_status"), default=IssueStatus.BACKLOG, server_default="backlog")
    priority: Mapped[IssuePriority] = mapped_column(enum_type(IssuePriority, "issue_priority"), default=IssuePriority.MEDIUM, server_default="medium")
    # Keep the documented storage field; the API calls the creator the reporter.
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reporter_id = synonym("created_by_id")
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    project: Mapped[Project] = relationship()
    reporter: Mapped[User] = relationship(foreign_keys=[created_by_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    sprint: Mapped[Sprint | None] = relationship()

    @property
    def issue_key(self) -> str:
        return f"{self.project.key}-{self.number}"
