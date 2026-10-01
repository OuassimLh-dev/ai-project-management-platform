from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.issue import Issue, IssuePriority, IssueType, enum_type
from app.models.user import User


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        CheckConstraint("length(trim(summary)) > 0 AND length(summary) <= 2000", name="ck_ai_analyses_summary"),
        CheckConstraint("length(trim(explanation)) > 0 AND length(explanation) <= 1000", name="ck_ai_analyses_explanation"),
        CheckConstraint("length(trim(model_name)) > 0 AND length(model_name) <= 200", name="ck_ai_analyses_model_name"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[str] = mapped_column(Text)
    suggested_type: Mapped[IssueType] = mapped_column(enum_type(IssueType, "ai_suggested_type"))
    suggested_priority: Mapped[IssuePriority] = mapped_column(enum_type(IssuePriority, "ai_suggested_priority"))
    explanation: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    issue: Mapped[Issue] = relationship()
    requested_by: Mapped[User] = relationship()
