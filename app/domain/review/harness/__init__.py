"""Trusted server-owned review instructions; never load repository-provided guidance."""

import hashlib
import json
from functools import lru_cache
from importlib.resources import files

from app.domain.review.empty_schema import FileCheck
from app.domain.review.verification import VerificationOutput

MODULES = (
    "core",
    "checks",
    "output",
    "java",
    "python",
    "javascript",
    "typescript",
    "verification",
    "empty_review",
)
LANGUAGES = {
    "java": "java",
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
}
MAX_SYSTEM_BYTES = 24576
COMPOSITION_REVISION = "selection-2-verifier-1-empty-recheck-1"


@lru_cache(maxsize=1)
def documents() -> dict[str, str]:
    root = files(__package__)
    return {name: root.joinpath(name + ".prompt").read_text(encoding="utf-8") for name in MODULES}


def version(schema: dict[str, object]) -> str:
    encoded = json.dumps(
        {
            "composition": COMPOSITION_REVISION,
            "documents": documents(),
            "schema": schema,
            "verification_schema": VerificationOutput.model_json_schema(),
            "empty_file_check_schema": FileCheck.model_json_schema(),
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode()
    return "rh1-" + hashlib.sha256(encoded).hexdigest()[:16]


def compose(payload: str, schema: dict[str, object]) -> tuple[str, dict[str, object]]:
    data = json.loads(payload)
    # The only selectors are fixed language aliases from server-prepared input.
    chosen = sorted(
        {LANGUAGES[f["language"]] for f in data["files"] if f.get("language") in LANGUAGES}
    )
    modules = ["core", "checks", "output", *chosen]
    text = "\n\n".join(documents()[name] for name in modules)
    text += "\n\nJSON schema: " + json.dumps(schema, sort_keys=True, ensure_ascii=False)
    if len(text.encode()) > MAX_SYSTEM_BYTES:
        raise ValueError("HARNESS_TOO_LARGE")
    return text, {
        "version": version(schema),
        "modules": modules,
        "system_digest": hashlib.sha256(text.encode()).hexdigest(),
    }


def compose_verification(payload: str) -> str:
    context = json.loads(payload)["context"]
    languages = sorted({LANGUAGES[f["language"]] for f in context["files"]})
    text = "\n\n".join(documents()[n] for n in ["core", "checks", *languages, "verification"])
    text += "\n\nVerification JSON schema: " + json.dumps(VerificationOutput.model_json_schema())
    if len(text.encode()) > MAX_SYSTEM_BYTES:
        raise ValueError("HARNESS_TOO_LARGE")
    return text


def compose_empty_review(payload: str, schema: dict[str, object]) -> str:
    data = json.loads(payload)
    languages = sorted({LANGUAGES[f["language"]] for f in data["files"]})
    text = "\n\n".join(documents()[n] for n in ["core", "checks", *languages, "empty_review"])
    text += "\n\nJSON schema: " + json.dumps(schema, ensure_ascii=False)
    if len(text.encode()) > MAX_SYSTEM_BYTES:
        raise ValueError("HARNESS_TOO_LARGE")
    return text
