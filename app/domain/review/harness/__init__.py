"""Trusted server-owned review instructions; never load repository-provided guidance."""

import hashlib
import json
from functools import lru_cache
from importlib.resources import files

MODULES = ("core", "checks", "output", "java", "python", "javascript", "typescript")
LANGUAGES = {
    "java": "java",
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
}
MAX_SYSTEM_BYTES = 24576
COMPOSITION_REVISION = "selection-1"


@lru_cache(maxsize=1)
def documents() -> dict[str, str]:
    root = files(__package__)
    return {name: root.joinpath(name + ".md").read_text(encoding="utf-8") for name in MODULES}


def version(schema: dict[str, object]) -> str:
    encoded = json.dumps(
        {"composition": COMPOSITION_REVISION, "documents": documents(), "schema": schema},
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
