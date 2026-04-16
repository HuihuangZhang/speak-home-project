from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from shared.db import Base
from shared.session_state import SessionStatus


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    room_name = Column(String, nullable=False, unique=True)
    status = Column(
        SQLEnum(SessionStatus),
        default=SessionStatus.CREATED,
        nullable=False,
    )
    exercise_plan = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    total_paused_seconds = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    summary = relationship("Summary", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant" | "note"
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    session = relationship("Session", back_populates="messages")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    exercises_covered = Column(JSON, nullable=True)
    coaching_notes = Column(String, nullable=True)
    next_session_recommendations = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending | done | failed
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    session = relationship("Session", back_populates="summary")
