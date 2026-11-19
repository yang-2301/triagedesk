"""Ticket endpoints: CRUD, state transitions, comments, AI triage."""
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..dependencies import get_db, get_current_user, require_roles
from ..models import Ticket, Comment, User, now_iso
from ..services.triage import build_triage
from ..services.sla import mark_first_response
from ..statemachine import validate, IllegalTransition

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

STATUSES = {"open", "in_progress", "resolved", "closed"}
PRIORITIES = {"urgent", "high", "normal", "low"}
CATEGORIES = {"billing", "bug", "feature", "account", "general"}


class TicketIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    priority: Optional[str] = None  # None => AI triage decides
    category: Optional[str] = None


class StatusIn(BaseModel):
    status: str


class AssignIn(BaseModel):
    assigned_to: Optional[str] = None


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    is_internal: bool = False


class TicketOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    category: str
    triage_source: str
    triage_confidence: Optional[str]
    suggested_reply: Optional[str]
    created_by: str
    assigned_to: Optional[str]
    created_at: str
    first_response_at: Optional[str]
    resolved_at: Optional[str]

    class Config:
        orm_mode = True


def _ticket_or_404(db: Session, ticket_id: str) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "ticket not found")
    return ticket


def _can_view(user: User, ticket: Ticket) -> bool:
    if user.role in ("agent", "admin"):
        return True
    return ticket.created_by == user.id


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(body: TicketIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Create a ticket. Unspecified category/priority are decided by the AI triager."""
    triage = build_triage().run(body.title, body.description)

    category = body.category or triage.category
    if category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {sorted(CATEGORIES)}")

    # Explicit priority wins; otherwise use the triager's, unless the triager
    # said 'low' on a customer ticket — bump to normal as a courtesy.
    priority = body.priority or triage.priority
    if priority == "low" and body.priority is None:
        priority = "normal"
    if priority not in PRIORITIES:
        raise HTTPException(422, f"priority must be one of {sorted(PRIORITIES)}")

    ticket = Ticket(
        title=body.title, description=body.description,
        category=category, priority=priority,
        triage_source=triage.source,
        triage_confidence=f"{triage.confidence:.2f}",
        suggested_reply=triage.suggested_reply,
        created_by=user.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=List[TicketOut])
def list_tickets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_q: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Paginated + filtered listing. Customers only see their own tickets."""
    query = db.query(Ticket).options(joinedload(Ticket.creator))
    if user.role == "customer":
        query = query.filter(Ticket.created_by == user.id)
    if status_q:
        if status_q not in STATUSES:
            raise HTTPException(422, "invalid status filter")
        query = query.filter(Ticket.status == status_q)
    if priority:
        if priority not in PRIORITIES:
            raise HTTPException(422, "invalid priority filter")
        query = query.filter(Ticket.priority == priority)
    if category:
        if category not in CATEGORIES:
            raise HTTPException(422, "invalid category filter")
        query = query.filter(Ticket.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(Ticket.title.ilike(like) | Ticket.description.ilike(like))

    offset = (page - 1) * page_size
    return query.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/mine", response_model=List[TicketOut])
def my_tickets(db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    return (db.query(Ticket).filter(Ticket.created_by == user.id)
            .order_by(Ticket.created_at.desc()).limit(50).all())


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    ticket = _ticket_or_404(db, ticket_id)
    if not _can_view(user, ticket):
        raise HTTPException(403, "not your ticket")
    return ticket


@router.post("/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: str, body: StatusIn,
                  db: Session = Depends(get_db),
                  user: User = Depends(require_roles("agent", "admin"))):
    """Status transitions, guarded by the state machine (422 on illegal move)."""
    ticket = _ticket_or_404(db, ticket_id)
    if body.status not in STATUSES:
        raise HTTPException(422, f"status must be one of {sorted(STATUSES)}")
    try:
        validate(ticket.status, body.status)
    except IllegalTransition as exc:
        raise HTTPException(422, str(exc)) from exc

    ticket.status = body.status
    now = now_iso()
    if body.status == "resolved":
        ticket.resolved_at = now
    elif body.status == "closed":
        ticket.closed_at = now
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign(ticket_id: str, body: AssignIn,
           db: Session = Depends(get_db),
           user: User = Depends(require_roles("admin"))):
    """Admin-only assignment. Agents pick up tickets via status change."""
    ticket = _ticket_or_404(db, ticket_id)
    if body.assigned_to is not None:
        target = db.get(User, body.assigned_to)
        if target is None or target.role not in ("agent", "admin"):
            raise HTTPException(422, "assignee must be an agent or admin")
    ticket.assigned_to = body.assigned_to
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/comments")
def list_comments(ticket_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    ticket = _ticket_or_404(db, ticket_id)
    if not _can_view(user, ticket):
        raise HTTPException(403, "not your ticket")
    comments = (db.query(Comment).filter(Comment.ticket_id == ticket_id)
                .order_by(Comment.created_at).all())
    visible = [c for c in comments
               if not c.is_internal or user.role in ("agent", "admin")]
    return [{"id": c.id, "author_id": c.author_id, "body": c.body,
             "is_internal": c.is_internal, "created_at": c.created_at}
            for c in visible]


@router.post("/{ticket_id}/comments", status_code=201)
def add_comment(ticket_id: str, body: CommentIn,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Add a comment. Any agent response starts the SLA clock.
    Internal notes are agent/admin-only; customers never see them."""
    ticket = _ticket_or_404(db, ticket_id)
    if not _can_view(user, ticket):
        raise HTTPException(403, "not your ticket")
    if body.is_internal and user.role not in ("agent", "admin"):
        raise HTTPException(403, "only staff can post internal notes")

    comment = Comment(ticket_id=ticket_id, author_id=user.id,
                      body=body.body, is_internal=body.is_internal)
    db.add(comment)

    # Staff public reply => first response for SLA purposes.
    if user.role in ("agent", "admin") and not body.is_internal:
        if mark_first_response(ticket):
            pass  # timestamp recorded on ticket

    db.commit()
    return {"id": comment.id, "created_at": comment.created_at,
            "is_internal": comment.is_internal}
