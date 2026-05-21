"""Pydantic schemas for chat endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""

    pass  # No body needed; customer_id comes from auth


class CreateSessionResponse(BaseModel):
    """Response after creating a chat session."""

    id: UUID
    customer_id: UUID
    message_count: int = 0
    created_at: datetime


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session."""

    content: str = Field(..., min_length=1, max_length=2000, description="User message content")


class ChatMessageResponse(BaseModel):
    """A single chat message."""

    id: UUID
    session_id: UUID
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""

    session_id: UUID
    messages: List[ChatMessageResponse] = Field(default_factory=list)
    message_count: int = 0


class RecommendationItem(BaseModel):
    """A single cake recommendation from AI."""

    product_name: str
    price: int
    reasoning: str


class AISummary(BaseModel):
    """Structured AI summary for order confirmation."""

    size: str
    flavor: str
    decorations: str
    pickup_date: str
    total_price: int


class ChatErrorResponse(BaseModel):
    """Error response for chat endpoints."""

    detail: str


class StreamMessageResponse(BaseModel):
    """Response metadata for streamed message (returned after stream completes)."""

    message_id: UUID
    session_id: UUID
    role: str = "assistant"
    content: str
    recommendations: Optional[List[RecommendationItem]] = None
    ai_summary: Optional[AISummary] = None
    created_at: datetime
