from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(trim(email))", name="ck_users_email_normalized"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @validates("email")
    def normalize_email(self, key: str, value: str) -> str:
        return value.strip().lower()
