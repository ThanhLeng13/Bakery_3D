"""Chat service - business logic for AI chatbot sessions and messages.

Handles:
- Chat session creation and management
- Message sending with Groq API integration (Llama 3.3 70B)
- SSE streaming responses
- Conversation context management (max 20 messages)
- Ordering agent: function calling against real catalogue data
- Error handling with fallback messages

Về trợ lý đặt bánh (ordering agent):
    LLM KHÔNG tự nghĩ ra tên bánh hay giá. Nó gọi công cụ trong `order_tools`,
    công cụ đọc CSDL rồi trả kết quả thật về cho LLM diễn đạt lại. Nhờ vậy giá
    luôn đúng và không thể bịa sản phẩm.

    Cách cũ (đã bỏ) nhồi cả danh mục vào prompt rồi bắt LLM viết JSON trong câu
    trả lời, sau đó dùng regex bóc lại — vừa dễ bịa giá, vừa vỡ khi LLM đổi cách
    trình bày.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, List, Optional

from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError

from app.core.config import settings
from app.services.order_tools import TOOL_SCHEMAS, OrderTools, dispatch
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Fallback message when AI API is unavailable
FALLBACK_ERROR_MESSAGE = (
    "Dịch vụ AI tạm thời không khả dụng. "
    "Vui lòng thử lại hoặc liên hệ cửa hàng qua số điện thoại."
)

MAX_MESSAGES_PER_SESSION = 20

# Trần số vòng gọi công cụ cho một lượt hỏi. Mỗi vòng là một lần gọi Groq, nên
# cần chặn để một LLM lặp vô hạn không treo request và không đốt token.
#
# Đặt 8 chứ không phải 4: một lượt chốt đơn hợp lệ cần tới 5 vòng — find_cakes →
# price_order → check_bake_time → create_draft_order → câu trả lời cuối. Với trần
# 4, đúng luồng này bị cắt ngang và đơn KHÔNG được tạo; đo thật chỉ đạt 1/3 lần.
# Vẫn đủ chặt để chặn vòng lặp bệnh hoạn.
MAX_TOOL_ROUNDS = 8


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
        self._order_tools = OrderTools(supabase_client)
        self._groq_client: Optional[AsyncGroq] = None

    def _execute_tool_call(self, name: str, raw_args: str, customer_id: Optional[str]) -> dict:
        """Chạy một công cụ do LLM yêu cầu, trả kết quả (hoặc lỗi) cho LLM đọc."""
        try:
            arguments = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            return {"error": f"Tham số không phải JSON hợp lệ: {raw_args[:120]}"}
        if not isinstance(arguments, dict):
            return {"error": "Tham số công cụ phải là một object JSON."}

        # Gắn customer_id cho công cụ tạo đơn. LLM không biết id này và cũng
        # không được phép tự khai — đơn phải thuộc đúng người đang chat.
        # (Cột orders.customer_id là NOT NULL, đã kiểm chứng bằng cách thử chèn.)
        if name == "create_draft_order":
            arguments["customer_id"] = customer_id
        return dispatch(self._order_tools, name, arguments)

    @staticmethod
    def _recommendations_from(tool_log: List[dict]) -> Optional[List[dict]]:
        """Lấy gợi ý bánh từ KẾT QUẢ CÔNG CỤ, không bóc từ chữ LLM viết.

        Nhờ vậy tên và giá trong thẻ gợi ý luôn khớp CSDL. Cách cũ dùng regex
        trên câu trả lời nên có thể ra tên bánh không tồn tại.
        """
        for entry in tool_log:
            result = entry.get("result") or {}
            cakes = result.get("cakes")
            if entry.get("tool") == "find_cakes" and cakes:
                return [
                    {
                        "product_name": c["name"],
                        "price": c["price"],
                        "reasoning": f"Phù hợp yêu cầu, cần đặt trước {c['needs_lead_hours']} giờ",
                        "product_id": c.get("id"),
                    }
                    for c in cakes[:5]
                ]
        return None

    @staticmethod
    def _summary_from(tool_log: List[dict]) -> Optional[dict]:
        """Lấy tóm tắt đơn từ kết quả `create_draft_order`."""
        for entry in reversed(tool_log):
            result = entry.get("result") or {}
            if entry.get("tool") == "create_draft_order" and result.get("created"):
                names = ", ".join(
                    f"{i['name']} x{i['quantity']}" for i in result.get("items", [])
                )
                return {
                    "size": "",
                    "flavor": "",
                    "decorations": names,
                    "pickup_date": result.get("pickup_date", ""),
                    "total_price": result.get("total_price", 0),
                    "order_id": result.get("order_id"),
                }
        return None

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

        # Call Groq API with the ordering-agent loop
        assistant_content, tool_log = await self._run_agent(
            system_prompt=system_prompt,
            conversation=conversation,
            customer_id=customer_id,
        )

        # Store assistant message
        assistant_msg = await self._store_message(
            session_id, "assistant", assistant_content
        )

        return {
            "message_id": assistant_msg["id"],
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_content,
            "recommendations": self._recommendations_from(tool_log),
            "ai_summary": self._summary_from(tool_log),
            "created_at": assistant_msg["created_at"],
        }

    async def _run_agent(
        self,
        system_prompt: str,
        conversation: List[dict],
        customer_id: Optional[str],
    ) -> tuple[str, List[dict]]:
        """Vòng lặp gọi công cụ (function calling) rồi trả lời khách.

        Trả về (nội dung trả lời, nhật ký công cụ đã gọi). Nhật ký dùng để lấy
        gợi ý bánh và tóm tắt đơn — lấy từ dữ liệu THẬT của công cụ, không phải
        bóc từ chữ LLM viết ra.

        Giới hạn MAX_TOOL_ROUNDS vòng để LLM lặp vô hạn không treo request.
        """
        client = self._get_groq_client()
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            *conversation,
        ]
        tool_log: List[dict] = []

        for round_index in range(MAX_TOOL_ROUNDS):
            try:
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    max_tokens=1024,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.error(f"Groq API error: {e}")
                raise AIServiceUnavailableError()
            except Exception as e:
                logger.error(f"Unexpected error calling Groq API: {e}")
                raise AIServiceUnavailableError()

            if not response.choices:
                logger.warning("Groq API returned no choices")
                raise AIServiceUnavailableError()

            message = response.choices[0].message
            calls = getattr(message, "tool_calls", None)

            # Không yêu cầu công cụ nữa -> đây là câu trả lời cuối.
            if not calls:
                content = message.content
                if not content:
                    logger.warning("Groq API returned empty content")
                    raise AIServiceUnavailableError()
                if round_index == 0 and not tool_log:
                    # Trả lời ngay mà không tra gì: có thể LLM tự bịa bánh/giá.
                    # Không chặn (câu hỏi xã giao không cần tra), nhưng ghi log
                    # để biết mà chỉnh prompt.
                    logger.info("Agent answered without calling any tool")
                return content, tool_log

            # LLM muốn gọi công cụ. Ghi lại lời gọi rồi chạy từng công cụ.
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments,
                        },
                    }
                    for c in calls
                ],
            })

            for call in calls:
                result = self._execute_tool_call(
                    call.function.name, call.function.arguments, customer_id
                )
                tool_log.append({"tool": call.function.name, "result": result})
                logger.info(
                    "Tool %s -> %s",
                    call.function.name,
                    json.dumps(result, ensure_ascii=False)[:200],
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        # Hết số vòng mà LLM vẫn đòi gọi công cụ. Trả lời dựa trên những gì đã có
        # thay vì treo request.
        logger.warning("Agent hit MAX_TOOL_ROUNDS (%s)", MAX_TOOL_ROUNDS)
        fallback = await self._force_final_answer(client, messages)
        return fallback, tool_log

    async def _force_final_answer(self, client: AsyncGroq, messages: list[dict]) -> str:
        """Buộc LLM trả lời bằng chữ, không cho gọi công cụ nữa.

        Phải gửi kèm `tools` + `tool_choice="none"`. Nếu bỏ hẳn `tools`, model
        vẫn có thể gọi công cụ theo quán tính và Groq trả lỗi 400
        "Tool choice is none, but model called a tool" — đã gặp thật.
        """
        try:
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                max_tokens=1024,
                messages=[
                    *messages,
                    {
                        "role": "system",
                        "content": (
                            "Đã tra đủ thông tin. Hãy trả lời khách NGAY bằng tiếng Việt, "
                            "dựa trên kết quả công cụ ở trên. Không gọi thêm công cụ."
                        ),
                    },
                ],
                tools=TOOL_SCHEMAS,
                tool_choice="none",
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            logger.error(f"Force-final-answer failed: {e}")
        raise AIServiceUnavailableError()

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

        # Chạy vòng lặp công cụ trước (không stream, vì phải chờ công cụ xong mới
        # biết trả lời gì), rồi stream phần chữ cuối cùng ra cho khách.
        full_response = ""
        tool_log: List[dict] = []
        try:
            client = self._get_groq_client()
            messages: list[dict] = [
                {"role": "system", "content": system_prompt},
                *conversation,
            ]
            answered = False

            for _round in range(MAX_TOOL_ROUNDS):
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    max_tokens=1024,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
                if not response.choices:
                    break
                message = response.choices[0].message
                calls = getattr(message, "tool_calls", None)

                if not calls:
                    # Không cần công cụ nữa -> stream câu trả lời cuối cho khách.
                    stream = await client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        max_tokens=1024,
                        messages=messages,
                        stream=True,
                    )
                    async with stream as s:
                        async for chunk in s:
                            if (
                                chunk.choices
                                and chunk.choices[0].delta is not None
                                and chunk.choices[0].delta.content
                            ):
                                text = chunk.choices[0].delta.content
                                full_response += text
                                yield f"data: {json.dumps({'type': 'content', 'text': text}, ensure_ascii=False)}\n\n"
                    answered = True
                    break

                # LLM muốn tra cứu. Báo cho giao diện biết đang tra, để khách
                # thấy phản hồi thay vì màn hình im lặng.
                yield f"data: {json.dumps({'type': 'tool', 'name': calls[0].function.name}, ensure_ascii=False)}\n\n"

                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.function.name,
                                "arguments": c.function.arguments,
                            },
                        }
                        for c in calls
                    ],
                })
                for call in calls:
                    result = self._execute_tool_call(
                        call.function.name, call.function.arguments, customer_id
                    )
                    tool_log.append({"tool": call.function.name, "result": result})
                    logger.info(
                        "Tool %s -> %s",
                        call.function.name,
                        json.dumps(result, ensure_ascii=False)[:200],
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            if not answered:
                # Hết vòng mà chưa trả lời được -> buộc trả lời bằng chữ.
                full_response = await self._force_final_answer(client, messages)
                for piece in _chunks(full_response):
                    yield f"data: {json.dumps({'type': 'content', 'text': piece}, ensure_ascii=False)}\n\n"

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

        # Gợi ý và tóm tắt lấy từ KẾT QUẢ CÔNG CỤ, không bóc từ chữ LLM viết.
        metadata = {
            "type": "done",
            "message_id": assistant_msg["id"],
            "recommendations": self._recommendations_from(tool_log),
            "ai_summary": self._summary_from(tool_log),
        }
        yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


def _chunks(text: str, size: int = 24) -> List[str]:
    """Cắt văn bản thành mẩu nhỏ để gửi dần, giống cảm giác streaming."""
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]

