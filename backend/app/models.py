"""SQLAlchemy models: users, tickets, comments."""
import uuid

from sqlalchemy import (Column, String, Text, Boolean,
                        ForeignKey, Index, create_engine)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from .config import DATABASE_URL

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# NOTE: keep timestamps as ISO strings for SQLite simplicity.
def now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def new_uuid() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"
    id = Column(String(12), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="customer")  # admin|agent|customer
    created_at = Column(String(32), nullable=False, default=now_iso)

    tickets = relationship("Ticket", foreign_keys="Ticket.created_by",
                           back_populates="creator")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String(12), primary_key=True, default=new_uuid)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open",
                    index=True)  # open|in_progress|resolved|closed
    priority = Column(String(10), nullable=False, default="normal",
                      index=True)  # urgent|high|normal|low
    category = Column(String(20), nullable=False, default="general")  # billing|bug|feature|account|general
    triage_source = Column(String(10), default="manual")  # ai|manual
    triage_confidence = Column(String(8))  # e.g. "0.87"
    suggested_reply = Column(Text)
    created_by = Column(String(12), ForeignKey("users.id"), nullable=False)
    assigned_to = Column(String(12), ForeignKey("users.id"), index=True)
    created_at = Column(String(32), nullable=False, default=now_iso)
    first_response_at = Column(String(32))
    resolved_at = Column(String(32))
    closed_at = Column(String(32))

    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to], remote_side=[User.id])
    comments = relationship("Comment", back_populates="ticket",
                            order_by="Comment.created_at",
                            cascade="all, delete-orphan")


Index("ix_tickets_status_priority", Ticket.status, Ticket.priority)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String(12), primary_key=True, default=new_uuid)
    ticket_id = Column(String(12), ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(String(12), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    is_internal = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(32), nullable=False, default=now_iso)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


def init_db() -> None:
    Base.metadata.create_all(engine)
