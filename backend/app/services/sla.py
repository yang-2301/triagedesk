"""SLA tracking: response-time targets per priority + breach detection."""
import datetime
from typing import List, Optional

from ..config import SLA_HOURS
from ..models import Ticket, now_iso


def sla_deadline(ticket: Ticket) -> Optional[datetime.datetime]:
    hours = SLA_HOURS.get(ticket.priority)
    if hours is None:
        return None
    created = datetime.datetime.fromisoformat(ticket.created_at)
    return created + datetime.timedelta(hours=hours)


def is_first_response_breached(ticket: Ticket) -> bool:
    """True when no agent response came within the SLA window."""
    deadline = sla_deadline(ticket)
    if deadline is None:
        return False
    if ticket.first_response_at:
        responded = datetime.datetime.fromisoformat(ticket.first_response_at)
        return responded > deadline
    if ticket.status in ("resolved", "closed"):
        return False  # ended without first response; tracked separately
    return datetime.datetime.now(datetime.timezone.utc) > deadline


def mark_first_response(ticket: Ticket, when: Optional[str] = None) -> bool:
    """Record the first agent response time. Returns True if it was the first."""
    if ticket.first_response_at:
        return False
    ticket.first_response_at = when or now_iso()
    return True


def breached_tickets(tickets: List[Ticket]) -> List[Ticket]:
    return [t for t in tickets if is_first_response_breached(t)]
