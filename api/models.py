"""Pydantic models for API request/response."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    message: str
    tools_used: list
    proactive: str | None
    chart_json: str | None
    cached: bool = False
