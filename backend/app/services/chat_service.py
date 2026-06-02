"""Chat service - business logic for AI chatbot sessions and messages.

Handles:
- Chat session creation and management
- Message sending with Groq API integration (Llama 3.3 70B)
- SSE streaming responses
- Conversation context management (max 20 messages)
- Recommendation extraction and AI_Summary generation
- Error handling with fallback messages
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, List, Optional

from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError

from app.core.config import settings
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Fallback message when AI API is unavailable
FALLBACK_ERROR_MESSAGE = (
    "Dịch vụ AI tạm thời không khả dụng. "
    "Vui lòng thử lại hoặc liên hệ cửa hàng qua số điện thoại."
)

MAX_MESSAGES_PER_SESSION = 20


class ChatServiceError(Exception):
    """Base exception for chat service errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SessionNotFoundError(ChatServiceError):
    """Chat session not found."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Chat session not found: {session_id}",
            status_code=404,
        )


class SessionLimitReachedError(ChatServiceError):
    """Chat session has reached the message limit."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Chat session has reached the maximum of {MAX_MESSAGES_PER_SESSION} messages: {session_id}",
            status_code=400,
        )


class AIServiceUnavailableError(ChatServiceError):
    """AI API is unavailable."""

    def __init__(self):
        super().__init__(
            FALLBACK_ERROR_MESSAGE,
            status_code=503,
        )


class ChatService:
    """Chat service for managing AI chatbot sessions and messages."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client
        self._rag_service = RAGService(supabase_client)
        self._groq_client: Optional[AsyncGroq] = None

    def _get_groq_client(self) -> AsyncGroq:
        """Get or create async Groq client instance."""
        if self._groq_client is None:
            if not settings.GROQ_API_KEY:
                raise AIServiceUnavailableError()
            self._groq_client = AsyncGroq(
                api_key=settings.GROQ_API_KEY
            )
        return self._groq_client

    async def create_session(self, customer_id: str) -> dict:
        """
        Create a new chat session for a customer.

        Args:
            customer_id: UUID string of the customer

        Returns:
            Dict with session data (id, customer_id, message_count, created_at)
        """
        result = (
            self._supabase.table("chat_sessions")
            .insert({
                "customer_id": customer_id,
                "message_count": 0,
            })
            .execute()
        )

        if not result.data:
            raise ChatServiceError("Failed to create chat session", status_code=500)

        session = result.data[0]
        return {
            "id": session["id"],
            "customer_id": session["customer_id"],
            "message_count": session["message_count"],
            "created_at": session["created_at"],
        }

    async def get_session(self, session_id: str, customer_id: str) -> dict:
        """
        Get a chat session by ID, verifying ownership.

        Args:
            session_id: UUID string of the session
            customer_id: UUID string of the customer (for ownership check)

        Returns:
            Session dict

        Raises:
            SessionNotFoundError: If session not found or not owned by customer
        """
        result = (
            self._supabase.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .eq("customer_id", customer_id)
            .maybe_single()
            .execute()
        )

        if result is None or result.data is None:
            raise SessionNotFoundError(session_id)

        return result.data

    async def get_chat_history(self, session_id: str, customer_id: str) -> dict:
        """
        Get chat history for a session.

        Args:
            session_id: UUID string of the session
            customer_id: UUID string of the customer (for ownership check)

        Returns:
            Dict with session_id, messages list, and message_count
        """
        # Verify session ownership
        session = await self.get_session(session_id, customer_id)

        # Fetch messages in chronological order
        result = (
            self._supabase.table("chat_messages")
            .select("id, session_id, role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        messages = result.data or []

        return {
            "session_id": session["id"],
            "messages": messages,
            "message_count": session["message_count"],
        }

    async def _get_conversation_context(self, session_id: str) -> List[dict]:
        """
        Get the last 20 messages for conversation context.

        Args:
            session_id: UUID string of the session

        Returns:
            List of message dicts with role and content, in chronological order
        """
        result = (
            self._supabase.table("chat_messages")
            .select("role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        messages = result.data or []

        # Limit to last 20 messages
        if len(messages) > MAX_MESSAGES_PER_SESSION:
            messages = messages[-MAX_MESSAGES_PER_SESSION:]

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

    async def _store_message(
        self, session_id: str, role: str, content: str
    ) -> dict:
        """
        Store a message in the database and update session message count.

        Args:
            session_id: UUID string of the session
            role: "user" or "assistant"
            content: Message content

        Returns:
            Stored message dict
        """
        # Insert message
        msg_result = (
            self._supabase.table("chat_messages")
            .insert({
                "session_id": session_id,
                "role": role,
                "content": content,
            })
            .execute()
        )

        if not msg_result.data:
            raise ChatServiceError("Failed to store message", status_code=500)

        # Update session message count and updated_at
        self._supabase.table("chat_sessions").update({
            "message_count": self._supabase.table("chat_sessions")
            .select("message_count")
            .eq("id", session_id)
            .execute()
            .data[0]["message_count"] + 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", session_id).execute()

        return msg_result.data[0]

    async def send_message(
        self, session_id: str, customer_id: str, content: str
    ) -> dict:
        """
        Send a message and get AI response (non-streaming).

        Args:
            session_id: UUID string of the session
            customer_id: UUID string of the customer
            content: User message content

        Returns:
            Dict with assistant message data, recommendations, and ai_summary

        Raises:
            SessionNotFoundError: If session not found
            SessionLimitReachedError: If session has reached message limit
            AIServiceUnavailableError: If Groq API fails
        """
        # Verify session ownership and check limits
        session = await self.get_session(session_id, customer_id)

        if session["message_count"] >= MAX_MESSAGES_PER_SESSION:
            raise SessionLimitReachedError(session_id)

        # Store user message
        await self._store_message(session_id, "user", content)

        # Get conversation context (including the just-stored user message)
        conversation = await self._get_conversation_context(session_id)

        # Build RAG context (with events + customer habits)
        system_prompt = await self._rag_service.build_context(
            customer_id=customer_id,
            exclude_session_id=session_id,
        )

        # Call Groq API
        try:
            client = self._get_groq_client()

            messages = [
                {"role": "system", "content": system_prompt},
                *conversation,
            ]

            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                max_tokens=1024,
                messages=messages,
            )

            assistant_content = None
            if response.choices and response.choices[0].message:
                assistant_content = response.choices[0].message.content

            if not assistant_content:
                logger.warning("Groq API returned empty or filtered response")
                raise AIServiceUnavailableError()

        except (APIError, APIConnectionError, RateLimitError) as e:
            logger.error(f"Groq API error: {e}")
            raise AIServiceUnavailableError()
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            raise AIServiceUnavailableError()

        # Store assistant message
        assistant_msg = await self._store_message(
            session_id, "assistant", assistant_content
        )

        # Extract recommendations and AI_Summary from response
        recommendations = extract_recommendations(assistant_content)
        ai_summary = extract_ai_summary(assistant_content)

        return {
            "message_id": assistant_msg["id"],
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_content,
            "recommendations": recommendations,
            "ai_summary": ai_summary,
            "created_at": assistant_msg["created_at"],
        }

    async def send_message_stream(
        self, session_id: str, customer_id: str, content: str
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream AI response via SSE.

        Args:
            session_id: UUID string of the session
            customer_id: UUID string of the customer
            content: User message content

        Yields:
            SSE-formatted strings with AI response chunks

        Raises:
            SessionNotFoundError: If session not found
            SessionLimitReachedError: If session has reached message limit
            AIServiceUnavailableError: If Groq API fails
        """
        # Verify session ownership and check limits
        session = await self.get_session(session_id, customer_id)

        if session["message_count"] >= MAX_MESSAGES_PER_SESSION:
            raise SessionLimitReachedError(session_id)

        # Store user message
        await self._store_message(session_id, "user", content)

        # Get conversation context
        conversation = await self._get_conversation_context(session_id)

        # Build RAG context (with events + customer habits)
        system_prompt = await self._rag_service.build_context(
            customer_id=customer_id,
            exclude_session_id=session_id,
        )

        # Stream from Groq API
        full_response = ""
        try:
            client = self._get_groq_client()

            messages = [
                {"role": "system", "content": system_prompt},
                *conversation,
            ]

            stream = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                max_tokens=1024,
                messages=messages,
                stream=True,
            )

            async for chunk in stream:
                if (
                    chunk.choices
                    and chunk.choices[0].delta is not None
                    and chunk.choices[0].delta.content
                ):
                    text = chunk.choices[0].delta.content
                    full_response += text
                    # Yield SSE formatted chunk
                    yield f"data: {json.dumps({'type': 'content', 'text': text}, ensure_ascii=False)}\n\n"

        except (APIError, APIConnectionError, RateLimitError) as e:
            logger.error(f"Groq API streaming error: {e}")
            error_data = json.dumps(
                {"type": "error", "message": FALLBACK_ERROR_MESSAGE},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
            return
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            error_data = json.dumps(
                {"type": "error", "message": FALLBACK_ERROR_MESSAGE},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Guard against empty stream response (content filtered or API issue)
        if not full_response:
            logger.warning("Groq API stream returned empty response")
            error_data = json.dumps(
                {"type": "error", "message": FALLBACK_ERROR_MESSAGE},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Store the complete assistant message
        assistant_msg = await self._store_message(
            session_id, "assistant", full_response
        )

        # Extract recommendations and AI_Summary
        recommendations = extract_recommendations(full_response)
        ai_summary = extract_ai_summary(full_response)

        # Send final metadata event
        metadata = {
            "type": "done",
            "message_id": assistant_msg["id"],
            "recommendations": recommendations,
            "ai_summary": ai_summary,
        }
        yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


def _parse_price(value: Any) -> int:
    """
    Robustly parse a price value that may be an int, float, or formatted
    string (e.g. "250.000đ", "250,000", "250000", "250k", "250.5k", "250K").

    In Vietnamese contexts, 'k' or 'K' is commonly used as a shorthand for
    thousands (e.g. "250k" = 250,000 VND, "250.5k" = 250,500 VND). The number
    before 'k' is parsed as a float to handle decimal values correctly, then
    multiplied by 1000. A plain 'k' not preceded by digits (e.g. "khuyến mãi")
    does NOT match.

    Args:
        value: Raw price value from parsed JSON

    Returns:
        Integer price in VND

    Raises:
        ValueError: If the value cannot be converted to an integer
    """
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip()

    # Detect Vietnamese "k" thousand shorthand: a number (int or float with
    # '.' or ',' as decimal separator) followed by k/K, then non-digit chars.
    # Parse the number part as float to correctly handle e.g. "250.5k" -> 250500
    # rather than stripping all non-digits which would give 2505 * 1000 = 2505000.
    k_match = re.search(r'(\d+[.,]?\d*)\s*[kK](?!\w)', text)
    if k_match:
        num_str = k_match.group(1).replace(',', '.')  # normalize decimal separator
        try:
            return int(float(num_str) * 1000)
        except ValueError:
            pass  # fall through to digit-strip fallback

    # Fallback: strip everything except digits
    digits = re.sub(r'[^\d]', '', text)
    if not digits:
        raise ValueError(f"Cannot parse price from: {value!r}")
    return int(digits)


def extract_recommendations(content: str) -> Optional[List[dict]]:
    """
    Extract cake recommendations from AI response content.

    Looks for structured recommendations with product name, price, and reasoning.
    Expected format in AI response: product name, price (VND), reasoning.

    Args:
        content: AI response text

    Returns:
        List of recommendation dicts or None if no recommendations found
    """
    recommendations = []

    # Try to find JSON array of recommendations
    json_pattern = r'\[[\s\S]*?\{[\s\S]*?"product_name"[\s\S]*?\}[\s\S]*?\]'
    json_match = re.search(json_pattern, content)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if all(k in item for k in ("product_name", "price", "reasoning")):
                        try:
                            recommendations.append({
                                "product_name": str(item["product_name"]),
                                "price": _parse_price(item["price"]),
                                "reasoning": str(item["reasoning"]),
                            })
                        except (ValueError, TypeError):
                            continue
                if 2 <= len(recommendations) <= 5:
                    return recommendations
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Try to extract from numbered list format
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match: digits (with separators) optionally followed by k/K shorthand,
        # then a currency marker (VND, đ, vnđ, dong). Group 1 is passed to
        # _parse_price which handles plain numbers, separators, and k/K suffix.
        price_match = re.search(
            r'(\d[\d.,]*(?:\s*[kK](?!\w))?)\s*(?:VND|đ|vnđ|dong)',
            line,
            re.IGNORECASE,
        )

        if price_match:
            try:
                price = _parse_price(price_match.group(1))
            except (ValueError, TypeError):
                continue

            name_part = line[:price_match.start()].strip()
            name_part = re.sub(r'^[\d]+[.)]\s*', '', name_part)
            name_part = re.sub(r'^[-*•]\s*', '', name_part)
            name_part = name_part.rstrip(" -–:,")

            if not name_part:
                continue

            reasoning_part = line[price_match.end():].strip()
            reasoning_part = reasoning_part.lstrip(" -–:,")

            if not reasoning_part:
                reasoning_part = "Phù hợp với yêu cầu của bạn"

            recommendations.append({
                "product_name": name_part,
                "price": price,
                "reasoning": reasoning_part,
            })

    if 2 <= len(recommendations) <= 5:
        return recommendations

    return None


def extract_ai_summary(content: str) -> Optional[dict]:
    """
    Extract AI_Summary JSON from AI response content.

    Looks for a JSON block with required fields: size, flavor, decorations,
    pickup_date, total_price.

    Args:
        content: AI response text

    Returns:
        AI_Summary dict or None if not found/incomplete
    """
    json_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    matches = re.findall(json_block_pattern, content)

    for match in matches:
        try:
            parsed = json.loads(match)
            required_fields = ["size", "flavor", "decorations", "pickup_date", "total_price"]
            if all(field in parsed for field in required_fields):
                if all(parsed.get(field) not in (None, "", 0) for field in required_fields):
                    return {
                        "size": str(parsed["size"]),
                        "flavor": str(parsed["flavor"]),
                        "decorations": str(parsed["decorations"]),
                        "pickup_date": str(parsed["pickup_date"]),
                        "total_price": _parse_price(parsed["total_price"]),
                    }
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    inline_pattern = r'\{[^{}]*"size"[^{}]*"flavor"[^{}]*"total_price"[^{}]*\}'
    inline_match = re.search(inline_pattern, content)
    if inline_match:
        try:
            parsed = json.loads(inline_match.group())
            required_fields = ["size", "flavor", "decorations", "pickup_date", "total_price"]
            if all(field in parsed for field in required_fields):
                if all(parsed.get(field) not in (None, "", 0) for field in required_fields):
                    return {
                        "size": str(parsed["size"]),
                        "flavor": str(parsed["flavor"]),
                        "decorations": str(parsed["decorations"]),
                        "pickup_date": str(parsed["pickup_date"]),
                        "total_price": _parse_price(parsed["total_price"]),
                    }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    return None
