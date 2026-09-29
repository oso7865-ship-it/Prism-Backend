"""Provider output contracts independent of prompt composition and runtime policy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    file_id: str = Field(max_length=8)
    symbol: str = Field(pattern=r"^[A-Za-z_][A-Za-z_0-9]{0,79}$")
    need: str = Field(min_length=1, max_length=160)


class ExpressionRepair(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    line: int = Field(ge=1)
    before: str = Field(min_length=1, max_length=160)
    after: str = Field(min_length=1, max_length=160)


class Issue(BaseModel):
    # Publish the same cross-field constraints that policy.validate_result enforces.
    # A provider must fix inconsistent output; the server never erases its premises.
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"basis": {"const": "SUPPORTED"}}},
                    "then": {"properties": {"assumptions": {"maxItems": 0}}},
                    "else": {
                        "properties": {
                            "assumptions": {"minItems": 1},
                            "severity": {"enum": ["INFO", "WARNING"]},
                        }
                    },
                }
            ],
        },
    )
    citations: list[str] = Field(default_factory=list, max_length=4)
    file_id: str = Field(max_length=8, description="Changed file containing the operation.")
    line: int = Field(ge=1, description="Provided HEAD line in this file.")
    severity: Literal["INFO", "WARNING", "ERROR"]
    basis: Literal["SUPPORTED", "NEEDS_CONTEXT"]
    evidence_lines: list[int] = Field(
        min_length=1,
        max_length=8,
        description="Unique provided lines in this file only; include line and a changed line.",
    )
    trigger: str = Field(
        min_length=1,
        max_length=400,
        description="Concrete input/conditions, including supplied contract preconditions.",
    )
    consequence: str = Field(
        min_length=1,
        max_length=400,
        description="Direct result for this trigger. No alternate branch or guessed effect.",
    )
    assumptions: list[str] = Field(
        max_length=3,
        description=(
            "Only UNKNOWN premises, not supplied types/defaults/contracts or language rules. "
            "SUPPORTED requires []."
        ),
    )
    title: str = Field(min_length=1, max_length=160)
    evidence: str = Field(min_length=1, max_length=800)
    suggestion: str = Field(min_length=1, max_length=800)
    contract_quote: str = Field(
        default="",
        max_length=240,
        description=(
            "Exact short quote from a supplied requirement/comment/assertion. "
            "Empty for language-only defects. Never infer intent from a name."
        ),
    )
    expression_repair: ExpressionRepair | None = Field(
        default=None,
        description="Optional exact Python return expression replacement. Never a code block.",
    )


class ReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=1600)
    issues: list[Issue] = Field(max_length=10)
    limitations: str = Field(min_length=1, max_length=1600)
    context_requests: list[ContextRequest] = Field(default_factory=list, max_length=2)
