"""Dashboard aggregates for agents/admins: counts, SLA breaches, 7-day trend."""
import datetime
from collections import Counter
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..models import Ticket
from ..services.sla import is_first_response_breached

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db),
              user=Depends(require_roles("agent", "admin"))):
    tickets: List[Ticket] = db.query(Ticket).all()

    by_status = Counter(t.status for t in tickets)
    by_priority = Counter(t.priority for t in tickets)
    by_category = Counter(t.category for t in tickets)

    breaches = [t for t in tickets if is_first_response_breached(t)]

    today = datetime.datetime.now(datetime.timezone.utc).date()
    trend = []
    for offset in range(6, -1, -1):
        day = today - datetime.timedelta(days=offset)
        day_key = day.isoformat()
        created = sum(1 for t in tickets if t.created_at[:10] == day_key)
        resolved = sum(1 for t in tickets if t.resolved_at and t.resolved_at[:10] == day_key)
        trend.append({"date": day_key, "created": created, "resolved": resolved})

    first_responses = [
        (datetime.datetime.fromisoformat(t.first_response_at)
         - datetime.datetime.fromisoformat(t.created_at)).total_seconds() / 3600
        for t in tickets if t.first_response_at
    ]
    median_hours = sorted(first_responses)[len(first_responses) // 2] if first_responses else None

    return {
        "total": len(tickets),
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "by_category": dict(by_category),
        "sla_breach_count": len(breaches),
        "sla_breach_rate": round(len(breaches) / len(tickets), 3) if tickets else 0.0,
        "breached_tickets": [
            {"id": t.id, "title": t.title, "priority": t.priority,
             "created_at": t.created_at} for t in breaches[:10]
        ],
        "median_first_response_hours": round(median_hours, 1) if median_hours is not None else None,
        "trend": trend,
    }
