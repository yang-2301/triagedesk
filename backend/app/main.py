"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import init_db
from .routers import auth, tickets, dashboard

app = FastAPI(
    title="TriageDesk API",
    version="1.0.0",
    description="Support desk with automatic AI triage — FastAPI + SQLAlchemy + JWT + RBAC.",
)

# The Vue dev server runs on 5173; docker uses the same origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "triagedesk", "version": app.version}


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
