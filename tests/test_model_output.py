import json

import pytest
from pydantic import ValidationError

from app.domain.review.model_output import strip_api_metadata
from app.domain.review.verification import VerificationOutput

BODY = {"decisions": [], "new_findings": [], "file_checks": []}


def test_only_the_echoed_json_mode_flag_is_removed():
    raw = json.dumps({"type": "json_object", **BODY})
    assert json.loads(strip_api_metadata(raw)) == BODY
    VerificationOutput.model_validate_json(strip_api_metadata(raw))


@pytest.mark.parametrize(
    "raw",
    [
        json.dumps({"type": "text", **BODY}),
        json.dumps({"decisions": [], "new_findings": [], "file_checks": [], "kind": "x"}),
        json.dumps({"nested": {"type": "json_object"}, **BODY}),
        "[1, 2]",
        "not json",
    ],
)
def test_everything_else_is_left_for_strict_validation(raw):
    assert strip_api_metadata(raw) == raw
    if raw.startswith("{"):
        with pytest.raises(ValidationError):
            VerificationOutput.model_validate_json(strip_api_metadata(raw))


def test_another_unknown_key_still_fails_even_with_the_flag():
    raw = json.dumps({"type": "json_object", "extra": 1, **BODY})
    with pytest.raises(ValidationError):
        VerificationOutput.model_validate_json(strip_api_metadata(raw))
