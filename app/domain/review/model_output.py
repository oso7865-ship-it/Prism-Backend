"""Normalization of raw model output before strict schema validation."""

import json


def strip_api_metadata(raw: str) -> str:
    """Drop exactly the echoed JSON-mode flag ``"type": "json_object"`` at the top level.

    The provider's JSON mode is sometimes echoed into the answer. Every other unknown key,
    any other value and any nested occurrence still fail the strict schema.
    """
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(value, dict) and value.get("type") == "json_object":
        del value["type"]
        return json.dumps(value, ensure_ascii=False)
    return raw
