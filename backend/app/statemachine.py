"""Ticket lifecycle state machine.

Legal transitions:

    open -> in_progress -> resolved -> closed
      |            |
      |            +-> open          (re-opened before resolution)
      +-> closed                   (customer closed without agent action)

Any other transition raises IllegalTransition.
"""
from typing import Set

LEGAL: dict = {
    "open": {"in_progress", "closed"},
    "in_progress": {"resolved", "open"},
    "resolved": {"closed", "in_progress"},
    "closed": set(),
}


class IllegalTransition(ValueError):
    def __init__(self, src: str, dst: str):
        self.src, self.dst = src, dst
        super().__init__(f"illegal transition: {src} -> {dst}")


def validate(src: str, dst: str) -> None:
    if dst not in LEGAL.get(src, set()):
        raise IllegalTransition(src, dst)


def is_terminal(status: str) -> bool:
    return status == "closed"
