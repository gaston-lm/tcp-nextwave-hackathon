from datetime import datetime

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    as_of: datetime | None = None
    max_steps: int = Field(default=12, ge=1, le=20)


class InvestigationResponse(BaseModel):
    result: str
    steps_used: int
