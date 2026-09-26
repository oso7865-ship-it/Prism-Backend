"""GitHub protocol validation; never retain payload or reflect parser errors."""

import hashlib
import hmac
import json
import re
from dataclasses import dataclass

from app.domain.webhook.exceptions import WebhookRejected

MAX_BODY = 1024 * 1024
PR_ACTIONS = {
    "opened",
    "reopened",
    "synchronize",
    "ready_for_review",
    "converted_to_draft",
    "closed",
    "edited",
}


@dataclass(frozen=True)
class Event:
    delivery_id: str
    event: str
    action: str
    installation_id: int
    repository_id: int | None
    number: int | None
    affected: list[int]
    digest: str


def positive(value: object) -> int:
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError
    return value


def verify(body: bytes, signature: str, secret: str, delivery: str, event: str) -> Event | None:
    if len(body) > MAX_BODY:
        raise WebhookRejected("WEBHOOK_BODY_TOO_LARGE")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not re.fullmatch(r"sha256=[0-9a-f]{64}", signature) or not hmac.compare_digest(
        signature, expected
    ):
        raise WebhookRejected("WEBHOOK_SIGNATURE_INVALID")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", delivery):
        raise WebhookRejected("WEBHOOK_DELIVERY_INVALID")
    if event not in {"pull_request", "installation", "installation_repositories"}:
        return None
    try:
        data = json.loads(body)
        action = data["action"]
        allowed = (
            PR_ACTIONS
            if event == "pull_request"
            else {"deleted", "suspend"}
            if event == "installation"
            else {"removed"}
        )
        if not isinstance(action, str) or action not in allowed:
            return None
        installation = positive(data["installation"]["id"])
        rid, number, affected = None, None, []
        if event == "pull_request":
            rid = positive(data["repository"]["id"])
            number = positive(data["number"])
            if number > 2**31 - 1:
                raise ValueError
        elif event == "installation_repositories":
            removed = data["repositories_removed"]
            if not isinstance(removed, list) or len(removed) > 10000:
                raise ValueError
            affected = sorted({positive(item["id"]) for item in removed})
        return Event(
            delivery,
            event,
            action,
            installation,
            rid,
            number,
            affected,
            hashlib.sha256(body).hexdigest(),
        )
    except (ValueError, KeyError, TypeError, RecursionError):
        raise WebhookRejected("WEBHOOK_PAYLOAD_INVALID") from None
