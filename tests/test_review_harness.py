import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.domain.review import harness
from app.domain.review.harness.evaluation import score
from app.domain.review.policy import PROMPT, ReviewOutput, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.shared.config.settings import Settings

SCHEMA = ReviewOutput.model_json_schema()
CASES = json.loads(Path("evals/review-harness/cases.json").read_text(encoding="utf-8"))


def payload(*languages):
    return json.dumps(
        {
            "files": [
                {"language": lang, "lines": [{"code": "injected marker"}]} for lang in languages
            ]
        }
    )


@pytest.mark.parametrize(
    "lang,module",
    [
        ("java", "java"),
        ("py", "python"),
        ("js", "javascript"),
        ("jsx", "javascript"),
        ("ts", "typescript"),
        ("tsx", "typescript"),
    ],
)
def test_fixed_module_selection_and_untrusted_text_separation(lang, module):
    text, metadata = harness.compose(payload(lang, lang, "../../core"), SCHEMA)
    assert metadata["modules"] == ["core", "checks", "output", module]
    assert "injected marker" not in text
    assert "untrusted" in text and "No tools" in text
    assert metadata["version"] == PROMPT
    assert len(text.encode()) <= harness.MAX_SYSTEM_BYTES
    assert len(metadata["system_digest"]) == 64


def test_digest_tracks_documents_schema_and_selected_system(monkeypatch):
    before = harness.version(SCHEMA)
    _, java = harness.compose(payload("java"), SCHEMA)
    _, python = harness.compose(payload("py"), SCHEMA)
    assert java["version"] == python["version"]
    assert java["system_digest"] != python["system_digest"]
    assert harness.version({**SCHEMA, "description": "changed"}) != before
    docs = dict(harness.documents())
    docs["core"] += "Changed instructions."
    monkeypatch.setattr(harness, "documents", lambda: docs)
    assert harness.version(SCHEMA) != before
    docs["core"] = "x" * harness.MAX_SYSTEM_BYTES
    with pytest.raises(ValueError, match="HARNESS_TOO_LARGE"):
        harness.compose(payload("java"), SCHEMA)


def output(lines):
    return {
        "summary": "제공 코드 검토",
        "limitations": "호출부와 실행 결과는 미검증",
        "issues": [
            {
                "file_id": "f1",
                "line": line,
                "severity": "WARNING",
                "basis": "SUPPORTED",
                "title": "검토 항목",
                "evidence": "제공한 줄에서 확인할 조건과 결과",
                "suggestion": "관련 경계 처리 검토",
            }
            for line in lines
        ],
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_evaluation_reference_and_missed_or_false_positive(case):
    # These are reference scorer checks, NOT model-generated semantic evaluations.
    assert score(case, output(case["expected_lines"]))["passed"]
    wrong = output([] if case["expected_lines"] else [1])
    assert not score(case, wrong)["passed"]


def test_uncertain_error_and_unanchored_claim_are_rejected():
    bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])
    response = output([1])
    response["issues"][0].update(basis="NEEDS_CONTEXT", severity="ERROR")
    with pytest.raises(ValueError, match="UNSUPPORTED_SEVERITY"):
        validate_result(json.dumps(response), bundle)
    response["issues"][0].update(basis="SUPPORTED", severity="WARNING", line=99)
    assert not score(CASES[0], response)["valid"]


def test_provider_actually_uses_harness_and_keeps_code_in_human_message(monkeypatch):
    captured = {}

    class FakeChat:
        def __init__(self, **kwargs):
            captured["settings"] = kwargs

        def bind(self, **kwargs):
            return self

        async def ainvoke(self, messages, config):
            captured["messages"], captured["config"] = messages, config
            return SimpleNamespace(
                content=json.dumps(output([])),
                usage_metadata={"input_tokens": 100, "output_tokens": 20},
                response_metadata={"finish_reason": "stop"},
            )

    monkeypatch.setattr("app.domain.review.provider.ChatDeepSeek", FakeChat)
    settings = Settings(_env_file=None, ai_enabled=False).model_copy(
        update={"ai_enabled": True, "deepseek_api_key": SecretStr("test-only-not-a-key")}
    )
    data = payload("java")
    result = asyncio.run(DeepSeekProvider(settings).review(data))
    system, human = captured["messages"]
    expected, _ = harness.compose(data, SCHEMA)
    assert system.type == "system" and system.content == expected
    assert human.type == "human" and human.content == data
    assert captured["settings"]["max_retries"] == 0
    assert captured["config"] == {"callbacks": []}
    assert result[1:] == (100, 20)
