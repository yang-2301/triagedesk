"""End-to-end API tests: auth, RBAC, state machine, triage, SLA, comments."""
import os
import tempfile

# Isolated DB per test run — must be set before app models import.
_tmpdir = tempfile.mkdtemp()
os.environ["TRIAGEDESK_DB"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"
os.environ.pop("OPENAI_API_KEY", None)  # force local triage in tests

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import init_db, SessionLocal, engine, Base, User
from app.security import hash_password
from app.ml.classifier import NaiveBayesClassifier
from app.ml import corpus
from app.services.triage import build_triage


@pytest.fixture(scope="module", autouse=True)
def _db():
    Base.metadata.drop_all(engine)
    init_db()
    db = SessionLocal()
    db.add_all([
        User(email="admin@t.dev", name="A", role="admin", password_hash=hash_password("admin-pass-123")),
        User(email="agent@t.dev", name="G", role="agent", password_hash=hash_password("agent-pass-123")),
        User(email="cust@t.dev", name="C", role="customer", password_hash=hash_password("cust-pass-123")),
    ])
    db.commit()
    yield
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def agent_headers(client):
    return _login(client, "agent@t.dev", "agent-pass-123")


@pytest.fixture(scope="module")
def cust_headers(client):
    return _login(client, "cust@t.dev", "cust-pass-123")


# --- auth -------------------------------------------------------------------

def test_register_customer_only(client):
    r = client.post("/api/auth/register", json={
        "email": "new@t.dev", "password": "password-123", "name": "N", "role": "admin"})
    assert r.status_code == 400


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "cust@t.dev", "password": "wrong"})
    assert r.status_code == 401


# --- RBAC -------------------------------------------------------------------

def test_dashboard_forbidden_for_customer(client, cust_headers):
    assert client.get("/api/dashboard", headers=cust_headers).status_code == 403


def test_dashboard_open_for_agent(client, agent_headers):
    assert client.get("/api/dashboard", headers=agent_headers).status_code == 200


def test_assign_agent_forbidden_by_admin_only(client, agent_headers):
    r = client.post("/api/tickets/x/assign", json={"assigned_to": None}, headers=agent_headers)
    assert r.status_code == 403


# --- triage -----------------------------------------------------------------

def test_create_ticket_auto_triages(client, cust_headers):
    r = client.post("/api/tickets", headers=cust_headers, json={
        "title": "Charged twice on my card",
        "description": "I was charged twice this month for the renewal, need a refund of the duplicate $99 charge."})
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "billing"
    assert body["triage_source"] == "ai"
    assert body["priority"] in ("high", "urgent")
    assert body["suggested_reply"]


def test_explicit_priority_overrides_ai(client, cust_headers):
    r = client.post("/api/tickets", headers=cust_headers, json={
        "title": "Where is your status page?",
        "description": "Just want to subscribe to incident updates, nothing broken.",
        "priority": "low"})
    assert r.json()["priority"] == "low"


def test_invalid_priority_rejected(client, cust_headers):
    r = client.post("/api/tickets", headers=cust_headers, json={
        "title": "test ticket", "description": "nothing here", "priority": "asap"})
    assert r.status_code == 422


# --- classifier quality ------------------------------------------------------

def test_classifier_accuracy_on_unseen_wording():
    clf = NaiveBayesClassifier(alpha=0.3)
    clf.fit(corpus.generate())
    eval_set = corpus.generate_eval()
    correct = sum(1 for label, text in eval_set if clf.predict(text)[0] == label)
    accuracy = correct / len(eval_set)
    assert accuracy >= 0.85, f"accuracy {accuracy:.2f} below 0.85 bar"


# --- state machine -----------------------------------------------------------

def _mk_agent_ticket(client, agent_headers):
    r = client.post("/api/tickets", headers=agent_headers, json={
        "title": "State machine test", "description": "For transition testing."})
    return r.json()["id"]


def test_legal_transition_path(client, agent_headers):
    tid = _mk_agent_ticket(client, agent_headers)
    for target in ("in_progress", "resolved", "closed"):
        r = client.post(f"/api/tickets/{tid}/status", headers=agent_headers,
                        json={"status": target})
        assert r.status_code == 200
    assert client.get(f"/api/tickets/{tid}", headers=agent_headers).json()["status"] == "closed"


def test_illegal_transition_rejected(client, agent_headers):
    tid = _mk_agent_ticket(client, agent_headers)
    # open -> resolved skips in_progress
    r = client.post(f"/api/tickets/{tid}/status", headers=agent_headers,
                    json={"status": "resolved"})
    assert r.status_code == 422


def test_closed_is_terminal(client, agent_headers):
    tid = _mk_agent_ticket(client, agent_headers)
    client.post(f"/api/tickets/{tid}/status", headers=agent_headers, json={"status": "closed"})
    r = client.post(f"/api/tickets/{tid}/status", headers=agent_headers,
                    json={"status": "in_progress"})
    assert r.status_code == 422


# --- comments & SLA ----------------------------------------------------------

def _mk_cust_ticket(client, cust_headers):
    r = client.post("/api/tickets", headers=cust_headers, json={
        "title": "Comment visibility test", "description": "For comment visibility testing."})
    return r.json()["id"]


def test_internal_note_hidden_from_customer(client, cust_headers, agent_headers):
    tid = _mk_cust_ticket(client, cust_headers)
    r = client.post(f"/api/tickets/{tid}/comments", headers=agent_headers,
                    json={"body": "internal diagnosis", "is_internal": True})
    assert r.status_code == 201

    seen = client.get(f"/api/tickets/{tid}/comments", headers=cust_headers).json()
    assert all(not c["is_internal"] for c in seen)
    seen_agent = client.get(f"/api/tickets/{tid}/comments", headers=agent_headers).json()
    assert any(c["is_internal"] for c in seen_agent)


def test_customer_cannot_post_internal_note(client, cust_headers, agent_headers):
    tid = _mk_cust_ticket(client, cust_headers)
    r = client.post(f"/api/tickets/{tid}/comments", headers=cust_headers,
                    json={"body": "sneaky", "is_internal": True})
    assert r.status_code == 403


def test_first_response_sets_sla_clock(client, agent_headers):
    tid = _mk_agent_ticket(client, agent_headers)
    before = client.get(f"/api/tickets/{tid}", headers=agent_headers).json()
    assert before["first_response_at"] is None
    client.post(f"/api/tickets/{tid}/comments", headers=agent_headers,
                json={"body": "looking into this now"})
    after = client.get(f"/api/tickets/{tid}", headers=agent_headers).json()
    assert after["first_response_at"] is not None


# --- access control on tickets ----------------------------------------------

def test_customer_cannot_read_others_tickets(client, cust_headers, agent_headers):
    tid = _mk_agent_ticket(client, agent_headers)
    assert client.get(f"/api/tickets/{tid}", headers=cust_headers).status_code == 403
    mine = client.get("/api/tickets", headers=cust_headers)
    assert all(t["created_by"] != "agent" for t in mine.json())
