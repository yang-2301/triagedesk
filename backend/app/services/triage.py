"""Triage service: classify incoming tickets (category + priority) and draft a suggested reply.

Strategy pattern:
  - LocalTriage: pure-python Naive Bayes + keyword priority rules (offline default)
  - LlmTriage:   OpenAI-backed, selected automatically when OPENAI_API_KEY is set
"""
import os
import re
from typing import Optional

from ..ml.classifier import NaiveBayesClassifier
from ..ml import corpus

# Singleton classifier, trained once at import (200 samples, ~ms cost).
_classifier: Optional[NaiveBayesClassifier] = None


def get_classifier() -> NaiveBayesClassifier:
    global _classifier
    if _classifier is None:
        _classifier = NaiveBayesClassifier(alpha=0.3)
        _classifier.fit(corpus.generate())
    return _classifier


URGENT_HINTS = re.compile(
    r"\b(down|outage|production|security|breach|data loss|cannot log in|locked out|"
    r"urgent|asap|critical|payment failing|all users)\b", re.I)
HIGH_HINTS = re.compile(
    r"\b(blocker|blocked|broken|crash|fails|error|cannot|refund|charge[ds]?\b.*twice|"
    r"blocked|lost|missing|deadline|procurement)\b", re.I)


def _priority_from(text: str) -> str:
    if URGENT_HINTS.search(text):
        return "urgent"
    if HIGH_HINTS.search(text):
        return "high"
    return "normal"


class TriageResult:
    __slots__ = ("category", "priority", "confidence", "source", "suggested_reply")

    def __init__(self, category: str, priority: str, confidence: float,
                 source: str, suggested_reply: str):
        self.category = category
        self.priority = priority
        self.confidence = confidence
        self.source = source
        self.suggested_reply = suggested_reply


REPLY_TEMPLATES = {
    "billing": ("Thanks for reaching out about this billing issue. I've flagged it for our "
                "billing team and they will review the charges on your account within one "
                "business day. If the charge was made in error, the correction will appear "
                "on your next statement."),
    "bug": ("Thanks for the detailed report — I was able to reproduce the behaviour you "
            "describe. Our engineering team has it queued for investigation; I'll post "
            "updates on this ticket as work progresses. Could you share your app version "
            "and browser to help us narrow it down?"),
    "feature": ("Thanks for the suggestion! I've logged it in our feature tracker and shared "
                "it with the product team. We review requests every sprint and will let you "
                "know here if it's picked up. Meanwhile, is there a workaround that would "
                "help your team today?"),
    "account": ("Sorry for the trouble with your account. I've sent a verification link to "
                "your registered email — follow it to regain access. If it doesn't arrive "
                "within a few minutes, check spam or reply here and I'll reset it manually."),
    "general": ("Thanks for your question! You can find detailed guidance in our help centre "
                "documentation. If anything there doesn't answer it, reply to this ticket "
                "and an agent will follow up within one business day."),
}


class LocalTriage:
    """Offline triage: NB category + rule priority + canned reply."""

    source = "ai"

    def run(self, title: str, description: str) -> TriageResult:
        text = f"{title} {description}"
        clf = get_classifier()
        category, confidence = clf.predict(text)
        priority = _priority_from(text)
        return TriageResult(category, priority, round(confidence, 2),
                            self.source, REPLY_TEMPLATES[category])


class LlmTriage:
    """OpenAI-backed triage. Same interface, richer replies."""

    source = "ai"

    def __init__(self, api_key: str, model: str):
        import json as _json
        import urllib.request
        self._json, self._urllib = _json, urllib.request
        self.api_key, self.model = api_key, model

    def run(self, title: str, description: str) -> TriageResult:
        prompt = (
            "You triage customer support tickets. Reply with ONLY a JSON object: "
            '{"category": one of ["billing","bug","feature","account","general"], '
            '"priority": one of ["urgent","high","normal","low"], '
            '"suggested_reply": 2-3 sentence professional response}.\n\n'
            f"Title: {title}\nDescription: {description}"
        )
        body = self._json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode()
        req = self._urllib.Request(
            "https://api.openai.com/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"})
        with self._urllib.urlopen(req, timeout=30) as resp:
            data = self._json.loads(resp.read())
        content = data["choices"][0]["message"]["content"]
        parsed = self._json.loads(content[content.find("{"): content.rfind("}") + 1])
        category = parsed.get("category", "general")
        priority = parsed.get("priority", "normal")
        if category not in REPLY_TEMPLATES:
            category = "general"
        if priority not in ("urgent", "high", "normal", "low"):
            priority = "normal"
        return TriageResult(category, priority, 0.95, self.source,
                            parsed.get("suggested_reply", REPLY_TEMPLATES[category]))


def build_triage():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        from ..config import LLM_MODEL
        return LlmTriage(api_key, LLM_MODEL)
    return LocalTriage()
