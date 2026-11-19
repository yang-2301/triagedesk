"""Synthetic training corpus for ticket triage.

Templates x slot-filling generate ~200 labelled samples. The eval set in
tests uses held-out templates (different phrasings, same distribution)
so we measure generalisation, not memorisation.
"""
import itertools
import random
from typing import List, Tuple

# --- per-class phrase banks -------------------------------------------------
# Each entry is (opening_variants, detail_variants, closing_variants); one
# sample = opening + detail (+ closing, sometimes).

BANK = {
    "billing": [
        ("I was charged twice this month", "my card shows two identical {amt} charges", "please refund the duplicate"),
        ("Why did my invoice increase", "the total jumped from {amt} to {amt2} with no explanation", "I need a corrected invoice"),
        ("My subscription renewed without warning", "I never approved the {amt} renewal", "cancel and refund it"),
        ("The coupon code did not apply", "checkout still charged full price of {amt}", "please honour the discount"),
        ("I need to update my billing email", "invoices still go to an old address", "confirm the change"),
        ("Refund request for unused months", "I paid {amt} but the service was down half of that period", "process the refund"),
        ("Card was declined but money left my account", "the bank says the {amt} charge is pending", "release the hold"),
        ("VAT number missing on receipt", "our finance team cannot file the {amt} invoice", "reissue with tax ID"),
    ],
    "bug": [
        ("The dashboard crashes on load", "stack trace appears after the spinner freezes for {sec}s", "this blocks our whole team"),
        ("Export to CSV produces empty files", "the download contains headers only, zero rows", "lost my weekly report"),
        ("Pagination breaks after page 3", "clicking next throws an error in console", "cannot reach older records"),
        ("Push notifications never arrive", "the mobile app shows subscribed but nothing comes through", "missing critical alerts"),
        ("Search returns wrong results", "query for {term} shows unrelated items instead", "results are useless"),
        ("File upload fails at 99%", "progress bar stalls and the request times out after {sec}s", "retry does not help"),
        ("Dark mode renders unreadable text", "labels are dark grey on black background", "accessibility issue"),
        ("API returns 500 intermittently", "roughly one in five calls to /v2/{term} fails", "our integration breaks"),
    ],
    "feature": [
        ("Can you add CSV export", "we need scheduled exports of the {term} report", "would save us hours weekly"),
        ("Please support SSO with Okta", "our security team requires SAML for all vendors", "this is a blocker for procurement"),
        ("Request: dark mode for the mobile app", "agents work night shifts and screens are too bright", "many of us would use it daily"),
        ("Add Slack notifications", "we want ticket updates posted to our #support channel", "currently we poll manually"),
        ("Webhook retries are too aggressive", "we would like configurable backoff for {term} events", "config option would suffice"),
        ("Support for bulk ticket merge", "duplicates pile up during incidents", "merge with a single action"),
        ("Custom fields on tickets", "we need to track {term} per ticket for compliance", "even a simple text field helps"),
        ("Role-based views", "contractors should not see billing dashboards", "fine-grained permissions"),
    ],
    "account": [
        ("Cannot reset my password", "the reset email never arrives", "locked out since yesterday"),
        ("Invite a new team member", "how do I add {name} as an agent", "need access this week"),
        ("Two-factor authentication trouble", "my authenticator codes are rejected", "cannot sign in at all"),
        ("Change account owner", "the previous admin left the company", "transfer ownership to {name}"),
        ("Account locked after failed logins", "I entered the wrong password {n} times", "please unlock"),
        ("Merge two workspaces", "we signed up twice with different emails", "keep the larger one"),
        ("Email change not saving", "the form accepts it but old email still logs in", "security concern"),
        ("Deleted my account by mistake", "workspace {name} is gone, need it restored", "contains client data"),
    ],
    "general": [
        ("Question about data retention", "how long do you keep deleted tickets", "for our compliance docs"),
        ("Do you have a status page", "we want to subscribe to incident updates", "please share the link"),
        ("Onboarding help for new agents", "is there a training video for the {term} workflow", "happy to read docs"),
        ("Where are your offices located", "need your address for vendor paperwork", "no urgency"),
        ("Trial extension request", "we need two more weeks to finish evaluation", "evaluation so far is positive"),
        ("Documentation for the API", "looking for rate limit details on {term} endpoints", "link appreciated"),
        ("Pricing for non-profits", "we are a registered charity, any discount", "budget is tight"),
        ("How do I contact support by phone", "prefer calling over email", "just a question"),
    ],
}

AMOUNTS = ["$29", "$49", "$99", "$199", "$249", "$299"]
TERMS = ["invoice", "analytics", "webhook", "report", "billing", "search"]
NAMES = ["Sarah", "Mike", "Elena", "Tom", "Priya", "Jon"]


def _fill(template: str, rng: random.Random) -> str:
    out = template
    repl = {
        "{amt}": rng.choice(AMOUNTS),
        "{amt2}": rng.choice(AMOUNTS),
        "{term}": rng.choice(TERMS),
        "{name}": rng.choice(NAMES),
        "{sec}": str(rng.choice([10, 15, 20, 30, 45, 60])),
        "{n}": str(rng.choice([3, 5, 6, 10])),
    }
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def generate(seed: int = 42, per_class: int = 40) -> List[Tuple[str, str]]:
    """Generate `per_class` samples per category, shuffled."""
    rng = random.Random(seed)
    samples: List[Tuple[str, str]] = []
    for label, entries in BANK.items():
        # Cycle through entries with different rng states until quota filled.
        cycle = itertools.cycle(entries)
        made = 0
        while made < per_class:
            opening, detail, closing = next(cycle)
            parts = [_fill(opening, rng), _fill(detail, rng)]
            if rng.random() < 0.7:
                parts.append(_fill(closing, rng))
            # occasionally add a filler prefix/suffix for surface variance
            if rng.random() < 0.3:
                parts.insert(0, rng.choice(["Hello,", "Hi team,", "To whom it may concern —", "Quick one:"]))
            if rng.random() < 0.3:
                parts.append(rng.choice(["Thanks!", "Best,", "Regards.", "Please advise."]))
            samples.append((label, " ".join(parts)))
            made += 1
    rng.shuffle(samples)
    return samples


def generate_holdout(seed: int = 7, per_class: int = 5) -> List[Tuple[str, str]]:
    """Smaller hold-out set drawn with a different RNG stream."""
    return generate(seed=seed, per_class=per_class)


# --- evaluation bank ---------------------------------------------------------
# Entirely different phrasings from the training bank: no shared sentence
# stems. This is what makes the reported accuracy meaningful — it measures
# generalisation to unseen wording, not template recall.
EVAL_BANK: List[Tuple[str, str]] = [
    ("billing", "You charged my card twice for the October invoice, reverse one of the charges"),
    ("billing", "Our monthly plan price went up without notice, explain the difference and issue a credit"),
    ("billing", "The annual renewal hit my card even though I cancelled last week, revert it"),
    ("billing", "Need a receipt with our tax ID on it for the accounting department"),
    ("billing", "The promo discount never showed up at checkout, adjust my payment"),
    ("billing", "Money was taken from my account but the subscription still shows unpaid"),
    ("bug", "The app freezes on the reports screen and never finishes loading"),
    ("bug", "Downloading our data gives a blank spreadsheet with no rows in it"),
    ("bug", "Going past the third page of the list view breaks with a JavaScript error"),
    ("bug", "Alerts stopped arriving on iOS even though everything says enabled"),
    ("bug", "Typing into the search box shows items that have nothing to do with my query"),
    ("bug", "Uploads hang near the end and eventually time out, even on small files"),
    ("feature", "It would help if we could schedule automatic weekly exports"),
    ("feature", "Any plan to add single sign-on via SAML? Compliance requires it"),
    ("feature", "A dark theme for the agent workspace would reduce eye strain at night"),
    ("feature", "Posting ticket updates into a Slack channel would replace our manual checks"),
    ("feature", "Please let us configure retry intervals for outgoing events"),
    ("feature", "Merging duplicate conversations in one click would save triage time"),
    ("account", "Password reset messages are not reaching my inbox, I cannot get in"),
    ("account", "How do I give a teammate agent permissions on our workspace"),
    ("account", "My authenticator app stopped working and I am locked out"),
    ("account", "Our old admin left the company, ownership needs to move to me"),
    ("account", "Too many failed logins got my profile blocked, restore access"),
    ("account", "I accidentally removed our workspace, is recovery possible"),
    ("general", "What is your policy on how long deleted data is stored"),
    ("general", "Is there a public uptime page I can subscribe to"),
    ("general", "Do you offer training material for new support agents"),
    ("general", "Could we get an extra two weeks to finish our pilot"),
    ("general", "What are the request limits for your public endpoints"),
    ("general", "Do registered charities get any pricing break"),
]


def generate_eval() -> List[Tuple[str, str]]:
    return list(EVAL_BANK)


if __name__ == "__main__":
    s = generate()
    from collections import Counter
    print(Counter(l for l, _ in s), "total", len(s))
