from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    status: str = Field(default="ok")
    message: str | None = None
