from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    trigger: str | None = Field(default=None, description="Requested run trigger")


class RunResponse(BaseModel):
    status: str = Field(default="not_implemented")
    detail: str = Field(default="Run execution is not implemented yet.")
