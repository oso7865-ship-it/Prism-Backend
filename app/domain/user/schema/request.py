from pydantic import BaseModel, ConfigDict

from app.shared.review_mode import ReviewMode


class PreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    review_mode: ReviewMode
