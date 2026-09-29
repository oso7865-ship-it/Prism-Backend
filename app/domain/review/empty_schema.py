from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FileCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    file_id: str = Field(max_length=8)
    # Legacy outputs may include a provided line. New prompts leave this to the server.
    line: int | None = Field(default=None, ge=1)
    outcome: Literal["FINDING", "NO_FINDING", "LIMITED"]
    observation: str = Field(min_length=1, max_length=240)
