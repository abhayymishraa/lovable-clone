from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Rate limiting fields
    last_query_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # A User can have many Chats.
    # back_populates="user" links back to the user field in the Chat model.
    # cascade="all, delete-orphan" → if a user is deleted, all their chats are deleted too (prevents orphaned chats).
    chats: Mapped[List["Chat"]] = relationship(
        "Chat", back_populates="user", cascade="all, delete-orphan"
    )

    def can_make_query(self) -> bool:
        """Check if user can make a query based on rate limiting"""

        if self.email == "grabhaymishra@gmail.com":
            return True

        if self.last_query_at is None:
            return True

        time_since_last_query = datetime.now(timezone.utc) - self.last_query_at
        return time_since_last_query.total_seconds() >= 86400  # 24 hours in seconds

    def update_last_query(self):
        """Update the last query timestamp"""
        self.last_query_at = datetime.now(timezone.utc)


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="chats")
