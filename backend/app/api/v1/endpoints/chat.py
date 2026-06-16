"""Chat API endpoints for AI chatbot.

Endpoints:
- POST /api/v1/chat/sessions - Create a new chat session
- POST /api/v1/chat/sessions/{session_id}/messages - Send message (SSE streaming response)
- GET /api/v1/chat/sessions/{session_id}/history - Get chat history
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user, require_customer, security_scheme, get_supabase_client
from app.schemas.chat import (
    ChatHistoryResponse,
    CreateSessionResponse,
    SendMessageRequest,
    StreamMessageResponse,
)
from app.services.chat_service import (
    AIServiceUnavailableError,
    ChatService,
    ChatServiceError,
    SessionLimitReachedError,
    SessionNotFoundError,
)

router = APIRouter()


def _get_chat_service(token: str | None = None) -> ChatService:
    """Create ChatService with service-role Supabase client.

    Authentication is verified upstream by require_customer.
    Service role is used to bypass RLS for chat operations.
    """
    client = get_supabase_client(token, use_service_role=True)
    return ChatService(client)


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    current_user: dict = Depends(require_customer),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Create a new chat session for the authenticated customer.

    Requires customer authentication.
    """
    token = credentials.credentials if credentials else None
    chat_service = _get_chat_service(token)

    try:
        result = await chat_service.create_session(
            customer_id=current_user["id"]
        )
        return result
    except ChatServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    stream: bool = Query(default=True, description="Whether to stream the response via SSE"),
    current_user: dict = Depends(require_customer),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Send a message in a chat session and receive AI response.

    By default, returns a streaming SSE response. Set stream=false for
    a regular JSON response.

    SSE events:
    - type: "content" - AI response text chunk
    - type: "error" - Error message
    - type: "done" - Stream complete with metadata (message_id, recommendations, ai_summary)
    - [DONE] - End of stream marker

    On Groq API error, returns 503 with fallback message.
    """
    token = credentials.credentials if credentials else None
    chat_service = _get_chat_service(token)

    try:
        if stream:
            # Return SSE streaming response
            event_generator = chat_service.send_message_stream(
                session_id=session_id,
                customer_id=current_user["id"],
                content=request.content,
            )
            return StreamingResponse(
                event_generator,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Return regular JSON response
            result = await chat_service.send_message(
                session_id=session_id,
                customer_id=current_user["id"],
                content=request.content,
            )
            return result

    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Chat session not found")
    except SessionLimitReachedError:
        raise HTTPException(
            status_code=400,
            detail="Chat session has reached the maximum message limit (20 messages)",
        )
    except AIServiceUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại hoặc liên hệ cửa hàng qua số điện thoại.",
        )
    except ChatServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(require_customer),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
):
    """
    Get chat history for a session.

    Returns all messages in chronological order.
    Only the session owner can access the history.
    """
    token = credentials.credentials if credentials else None
    chat_service = _get_chat_service(token)

    try:
        result = await chat_service.get_chat_history(
            session_id=session_id,
            customer_id=current_user["id"],
        )
        return result
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Chat session not found")
    except ChatServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
