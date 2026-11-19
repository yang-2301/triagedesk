"""Seed script: staff accounts + realistic demo tickets across the funnel."""
import datetime
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import init_db, SessionLocal, engine, User, Ticket, Comment
from app.security import hash_password
from app.services.triage import build_triage
from app.models import now_iso

TICKET_SEEDS = [
    ("Payment charged twice on renewal", "My card was charged twice for the September renewal, both $199. Need one reversed.", "customer1@demo.dev", "billing", "high", "open"),
    ("Dashboard blank after latest release", "Since this morning the analytics dashboard renders an empty white screen for all our agents. Production issue for our ops team.", "customer2@demo.dev", "bug", "urgent", "in_progress"),
    ("Request: SAML SSO with Okta", "Procurement requires SAML before we can roll this out to 200 seats. Is this on the roadmap?", "customer3@demo.dev", "feature", "normal", "open"),
    ("Cannot reset password", "The reset email never arrives, checked spam. Locked out since yesterday evening.", "customer1@demo.dev", "account", "high", "resolved"),
    ("CSV export empty", "Weekly export downloads fine but the file only has headers, zero rows.", "customer2@demo.dev", "bug", "normal", "in_progress"),
    ("Dark mode text unreadable", "In dark theme the table labels are grey on black, our agents cannot read them.", "customer3@demo.dev", "bug", "low", "open"),
    ("Invoice missing VAT number", "Our finance team cannot file the $499 invoice without the VAT ID. Please reissue.", "customer1@demo.dev", "billing", "normal", "open"),
    ("Webhook retries too aggressive", "Retries hit our endpoint every 30 seconds for hours. Would like configurable backoff.", "customer2@demo.dev", "feature", "low", "open"),
    ("Locked out after failed logins", "Entered the wrong password five times and the account is blocked now. Please unlock.", "customer3@demo.dev", "account", "high", "closed"),
    ("Do you have a status page?", "We want to subscribe to incident updates for your API.", "customer1@demo.dev", "general", "low", "closed"),
    ("Search shows unrelated results", "Querying 'webhook' in ticket search returns billing conversations from months ago.", "customer2@demo.dev", "bug", "normal", "open"),
    ("Bulk merge duplicates", "During incidents we accumulate dozens of duplicate tickets. One-click merge would save triage time.", "customer3@demo.dev", "feature", "normal", "open"),
]

REPLIES = {
    0: "Flagged for the billing team; they will review both charges within one business day and confirm here.",
    1: "Reproduced on our side — we rolled back the frontend release at 09:40 UTC and the dashboard is loading again. Root cause analysis to follow.",
    3: "Sent a fresh reset link from our mail provider with elevated deliverability; confirmed delivered this time.",
    4: "Engineer confirmed: exports with more than one filter lose row data. Fix targeted for the next patch release.",
    8: "Account unlocked and a password-reset link sent. Please update your password after signing in.",
    9: "Yes — status.demo.dev. You can subscribe per-component or for the whole platform.",
}

INTERNAL_NOTES = {
    1: "Rollback of build 2.14.3 at 09:40 UTC. Regression in chart bundle splitting. Postmortem doc linked internally.",
    4: "Root cause: multi-filter export path drops rows after the COUNT optimization. Fix in review, PR #482.",
}


def main(reset: bool = False) -> None:
    if reset:
        from app.models import Base
        Base.metadata.drop_all(engine)
    init_db()
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("Database already seeded — pass --reset to rebuild.")
        return

    admin = User(email="admin@demo.dev", name="Alex Rivera", role="admin",
                 password_hash=hash_password("admin-demo-1234"))
    agent = User(email="agent@demo.dev", name="Sam Chen", role="agent",
                 password_hash=hash_password("agent-demo-1234"))
    db.add_all([admin, agent])

    customers = []
    for i in (1, 2, 3):
        c = User(email=f"customer{i}@demo.dev", name=f"Customer {i}",
                 role="customer", password_hash=hash_password("customer-demo-1234"))
        customers.append(c)
        db.add(c)
    db.commit()

    rng = random.Random(11)
    triage = build_triage()
    today = datetime.datetime.now(datetime.timezone.utc)

    for idx, (title, desc, cust_email, cat, prio, status) in enumerate(TICKET_SEEDS):
        days_ago = rng.randint(0, 6)
        created = today - datetime.timedelta(days=days_ago, hours=rng.randint(1, 12))
        cust = next(c for c in customers if c.email == cust_email)

        t = Ticket(title=title, description=desc, category=cat, priority=prio,
                   status=status, created_by=cust.id,
                   created_at=created.isoformat(timespec="seconds"))
        # AI triage runs for confidence/source fields (category/priority pinned to seed).
        result = triage.run(title, desc)
        t.triage_source = "ai"
        t.triage_confidence = f"{result.confidence:.2f}"
        t.suggested_reply = result.suggested_reply

        if status != "open":
            t.assigned_to = agent.id
        if status in ("in_progress", "resolved", "closed"):
            resp = created + datetime.timedelta(hours=rng.uniform(0.5, 3))
            t.first_response_at = resp.isoformat(timespec="seconds")
        if status in ("resolved", "closed"):
            t.resolved_at = (resp + datetime.timedelta(hours=rng.uniform(2, 10))).isoformat(timespec="seconds")
        if status == "closed":
            resolved = datetime.datetime.fromisoformat(t.resolved_at)
            t.closed_at = (resolved + datetime.timedelta(hours=rng.uniform(4, 24))).isoformat(timespec="seconds")

        db.add(t)
        db.flush()

        if idx in REPLIES:
            author = agent if idx != 9 else admin
            db.add(Comment(ticket_id=t.id, author_id=author.id,
                           body=REPLIES[idx], is_internal=False,
                           created_at=t.first_response_at or now_iso()))
        if idx in INTERNAL_NOTES:
            db.add(Comment(ticket_id=t.id, author_id=agent.id,
                           body=INTERNAL_NOTES[idx], is_internal=True,
                           created_at=now_iso()))

    db.commit()
    counts = {r: db.query(Ticket).filter(Ticket.status == r).count() for r in ("open", "in_progress", "resolved", "closed")}
    print(f"Seeded: {db.query(User).count()} users, {db.query(Ticket).count()} tickets, by status {counts}")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
