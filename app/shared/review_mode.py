"""Server-owned review modes. Only these values may select a review harness.

A mode is chosen from this closed set (API validation, database CHECK and the harness loader all
use it). User-provided text is never part of a prompt path or of an instruction.
"""

from typing import Literal

ReviewMode = Literal["JUNIOR", "SENIOR"]
REVIEW_MODES: tuple[ReviewMode, ...] = ("JUNIOR", "SENIOR")
DEFAULT_REVIEW_MODE: ReviewMode = "SENIOR"


def parse_review_mode(value: object) -> ReviewMode:
    if value == "JUNIOR":
        return "JUNIOR"
    if value == "SENIOR":
        return "SENIOR"
    raise ValueError("INVALID_REVIEW_MODE")
