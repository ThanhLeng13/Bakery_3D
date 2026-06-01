"""Tests for chat service, RAG service, and AI response parsing.

Tests cover:
- RAG context building and product catalog formatting
- Recommendation extraction from AI responses
- AI_Summary extraction from AI responses
- Chat service session management
- Chat service message handling
- Error handling for Claude API failures
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.chat_service import (
    AIServiceUnavailableError,
    ChatService,
    ChatServiceError,
    SessionLimitReachedError,
    SessionNotFoundError,
    extract_ai_summary,
    extract_recommendations,
)
from app.services.rag_service import RAGService, SYSTEM_PROMPT_TEMPLATE


# ============================================================
# RAG Service Tests
# ============================================================


class TestRAGServiceFormatCatalog:
    """Tests for RAG context formatting."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.rag_service = RAGService(self.mock_supabase)

    def test_format_catalog_context_basic(self):
        """Format a basic product catalog into JSON context."""
        products = [
            {
                "name": "Bánh Sinh Nhật Dâu",
                "category": "bánh âu",
                "base_price": 350000,
                "sizes": [{"name": "16cm", "price": 350000}],
                "flavors": [{"name": "dâu", "price": 0}],
                "description": "Bánh sinh nhật vị dâu tươi",
            }
        ]

        result = self.rag_service.format_catalog_context(products)
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["name"] == "Bánh Sinh Nhật Dâu"
        assert parsed[0]["base_price"] == 350000
        assert parsed[0]["category"] == "bánh âu"

    def test_format_catalog_context_empty(self):
        """Format empty catalog returns empty JSON array."""
        result = self.rag_service.format_catalog_context([])
        parsed = json.loads(result)
        assert parsed == []

    def test_format_catalog_context_truncates_description(self):
        """Long descriptions are truncated to 200 chars."""
        products = [
            {
                "name": "Test",
                "category": "test",
                "base_price": 100000,
                "sizes": [],
                "flavors": [],
                "description": "A" * 300,
            }
        ]

        result = self.rag_service.format_catalog_context(products)
        parsed = json.loads(result)
        assert len(parsed[0]["description"]) == 200

    def test_format_catalog_context_handles_none_fields(self):
        """Handle None values in product fields gracefully."""
        products = [
            {
                "name": "Test",
                "category": "test",
                "base_price": 100000,
                "sizes": None,
                "flavors": None,
                "description": None,
            }
        ]

        result = self.rag_service.format_catalog_context(products)
        parsed = json.loads(result)
        assert parsed[0]["sizes"] == []
        assert parsed[0]["flavors"] == []
        assert parsed[0]["description"] == ""


class TestRAGServiceBuildSystemPrompt:
    """Tests for system prompt construction."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.rag_service = RAGService(self.mock_supabase)

    def test_build_system_prompt_contains_catalog(self):
        """System prompt includes the product catalog JSON."""
        catalog_json = '[{"name": "Test Cake", "base_price": 200000}]'
        result = self.rag_service.build_system_prompt(catalog_json)

        assert "Test Cake" in result
        assert "200000" in result
        assert "Bơ Nơ" in result
        assert "tiếng Việt" in result

    def test_build_system_prompt_contains_rules(self):
        """System prompt includes all conversation rules."""
        catalog_json = "[]"
        result = self.rag_service.build_system_prompt(catalog_json)

        assert "Luôn trả lời bằng tiếng Việt" in result
        assert "Chỉ gợi ý sản phẩm có trong danh mục" in result
        assert "Tối đa 5 gợi ý mỗi lần" in result
        assert "AI_Summary" in result


class TestRAGServiceFilterProducts:
    """Tests for product filtering by criteria."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.rag_service = RAGService(self.mock_supabase)
        self.products = [
            {
                "name": "Bánh nhỏ",
                "base_price": 200000,
                "sizes": [{"name": "16cm"}],
                "flavors": [],
            },
            {
                "name": "Bánh lớn",
                "base_price": 500000,
                "sizes": [{"name": "24cm"}],
                "flavors": [],
            },
            {
                "name": "Bánh 2 tầng",
                "base_price": 800000,
                "sizes": [{"name": "2-tier"}],
                "flavors": [],
            },
        ]

    @pytest.mark.asyncio
    async def test_filter_by_budget(self):
        """Filter products by maximum budget."""
        result = await self.rag_service.filter_products_by_criteria(
            self.products, budget=300000
        )
        assert len(result) == 1
        assert result[0]["name"] == "Bánh nhỏ"

    @pytest.mark.asyncio
    async def test_filter_by_size(self):
        """Filter products by size."""
        result = await self.rag_service.filter_products_by_criteria(
            self.products, size="24cm"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Bánh lớn"

    @pytest.mark.asyncio
    async def test_filter_no_match_returns_all(self):
        """When no products match, return all products."""
        result = await self.rag_service.filter_products_by_criteria(
            self.products, budget=100000
        )
        # No product under 100k, so return all
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_filter_no_criteria_returns_all(self):
        """No criteria returns all products."""
        result = await self.rag_service.filter_products_by_criteria(
            self.products
        )
        assert len(result) == 3


# ============================================================
# Recommendation Extraction Tests
# ============================================================


class TestExtractRecommendations:
    """Tests for extracting recommendations from AI responses."""

    def test_extract_from_json_array(self):
        """Extract recommendations from JSON array format."""
        content = """Dựa trên yêu cầu của bạn, tôi gợi ý:
[
  {"product_name": "Bánh Dâu", "price": 350000, "reasoning": "Phù hợp sinh nhật"},
  {"product_name": "Bánh Socola", "price": 400000, "reasoning": "Hương vị đậm đà"},
  {"product_name": "Bánh Matcha", "price": 380000, "reasoning": "Thanh mát, đẹp mắt"}
]"""
        result = extract_recommendations(content)
        assert result is not None
        assert len(result) == 3
        assert result[0]["product_name"] == "Bánh Dâu"
        assert result[0]["price"] == 350000
        assert result[0]["reasoning"] == "Phù hợp sinh nhật"

    def test_extract_from_numbered_list_with_vnd(self):
        """Extract recommendations from numbered list with VND prices."""
        content = """Tôi gợi ý cho bạn:
1. Bánh Dâu Tươi - 350000 VND - Phù hợp cho sinh nhật
2. Bánh Socola Đen - 400000 VND - Hương vị đậm đà cho người lớn
3. Bánh Matcha - 380000 VND - Thanh mát và đẹp mắt
"""
        result = extract_recommendations(content)
        assert result is not None
        assert len(result) == 3
        assert result[0]["product_name"] == "Bánh Dâu Tươi"
        assert result[0]["price"] == 350000

    def test_extract_from_list_with_dong_symbol(self):
        """Extract recommendations with đ price format."""
        content = """Gợi ý:
- Bánh Sinh Nhật Dâu, 350.000đ, Phù hợp sinh nhật trẻ em
- Bánh Kem Socola, 400.000đ, Hương vị yêu thích
- Bánh Tiramisu, 450.000đ, Sang trọng cho người lớn
"""
        result = extract_recommendations(content)
        assert result is not None
        assert len(result) == 3
        assert result[0]["price"] == 350000
        assert result[1]["price"] == 400000

    def test_no_recommendations_returns_none(self):
        """Return None when no recommendations found."""
        content = "Xin chào! Bạn muốn đặt bánh cho dịp gì ạ?"
        result = extract_recommendations(content)
        assert result is None

    def test_single_recommendation_returns_none(self):
        """Return None when fewer than 2 recommendations (need 2-5)."""
        content = "1. Bánh Dâu - 350000 VND - Phù hợp"
        result = extract_recommendations(content)
        assert result is None

    def test_more_than_5_recommendations_returns_none(self):
        """Return None when more than 5 recommendations."""
        lines = [
            f"{i}. Bánh {i} - {i*100000} VND - Lý do {i}"
            for i in range(1, 7)
        ]
        content = "\n".join(lines)
        result = extract_recommendations(content)
        assert result is None


# ============================================================
# AI Summary Extraction Tests
# ============================================================


class TestExtractAISummary:
    """Tests for extracting AI_Summary from AI responses."""

    def test_extract_from_code_block(self):
        """Extract AI_Summary from JSON code block."""
        content = """Đây là tóm tắt đơn hàng của bạn:
```json
{
  "size": "20cm",
  "flavor": "socola",
  "decorations": "hoa kem bơ, chữ Happy Birthday",
  "pickup_date": "2024-03-15",
  "total_price": 450000
}
```
Bạn xác nhận đặt hàng nhé?"""
        result = extract_ai_summary(content)
        assert result is not None
        assert result["size"] == "20cm"
        assert result["flavor"] == "socola"
        assert result["decorations"] == "hoa kem bơ, chữ Happy Birthday"
        assert result["pickup_date"] == "2024-03-15"
        assert result["total_price"] == 450000

    def test_extract_from_code_block_no_json_label(self):
        """Extract AI_Summary from code block without json label."""
        content = """Tóm tắt:
```
{
  "size": "16cm",
  "flavor": "dâu",
  "decorations": "topping dâu tươi",
  "pickup_date": "2024-04-01",
  "total_price": 350000
}
```"""
        result = extract_ai_summary(content)
        assert result is not None
        assert result["size"] == "16cm"
        assert result["total_price"] == 350000

    def test_missing_required_field_returns_none(self):
        """Return None when a required field is missing."""
        content = """```json
{
  "size": "20cm",
  "flavor": "socola",
  "decorations": "hoa kem",
  "pickup_date": "2024-03-15"
}
```"""
        # Missing total_price
        result = extract_ai_summary(content)
        assert result is None

    def test_empty_field_returns_none(self):
        """Return None when a required field is empty."""
        content = """```json
{
  "size": "",
  "flavor": "socola",
  "decorations": "hoa kem",
  "pickup_date": "2024-03-15",
  "total_price": 450000
}
```"""
        result = extract_ai_summary(content)
        assert result is None

    def test_zero_total_price_returns_none(self):
        """Return None when total_price is 0."""
        content = """```json
{
  "size": "20cm",
  "flavor": "socola",
  "decorations": "hoa kem",
  "pickup_date": "2024-03-15",
  "total_price": 0
}
```"""
        result = extract_ai_summary(content)
        assert result is None

    def test_no_summary_returns_none(self):
        """Return None when no AI_Summary found."""
        content = "Bạn muốn đặt bánh gì ạ?"
        result = extract_ai_summary(content)
        assert result is None


# ============================================================
# Chat Service Tests
# ============================================================


class TestChatServiceCreateSession:
    """Tests for chat session creation."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.chat_service = ChatService(self.mock_supabase)

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Successfully create a new chat session."""
        session_id = str(uuid4())
        customer_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        self.mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{
                "id": session_id,
                "customer_id": customer_id,
                "message_count": 0,
                "created_at": now,
            }]
        )

        result = await self.chat_service.create_session(customer_id)

        assert result["id"] == session_id
        assert result["customer_id"] == customer_id
        assert result["message_count"] == 0

    @pytest.mark.asyncio
    async def test_create_session_failure(self):
        """Raise error when session creation fails."""
        self.mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with pytest.raises(ChatServiceError):
            await self.chat_service.create_session(str(uuid4()))


class TestChatServiceGetSession:
    """Tests for getting a chat session."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.chat_service = ChatService(self.mock_supabase)

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Successfully get a session owned by the customer."""
        session_id = str(uuid4())
        customer_id = str(uuid4())

        mock_chain = MagicMock()
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "id": session_id,
                "customer_id": customer_id,
                "message_count": 5,
            }
        )

        result = await self.chat_service.get_session(session_id, customer_id)
        assert result["id"] == session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Raise SessionNotFoundError when session doesn't exist."""
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        with pytest.raises(SessionNotFoundError):
            await self.chat_service.get_session(str(uuid4()), str(uuid4()))


class TestChatServiceGetHistory:
    """Tests for getting chat history."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.chat_service = ChatService(self.mock_supabase)

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self):
        """Get chat history returns messages in chronological order."""
        session_id = str(uuid4())
        customer_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Mock get_session
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "id": session_id,
                "customer_id": customer_id,
                "message_count": 2,
            }
        )

        # Mock get messages
        self.mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "session_id": session_id, "role": "user", "content": "Xin chào", "created_at": now},
                {"id": str(uuid4()), "session_id": session_id, "role": "assistant", "content": "Chào bạn!", "created_at": now},
            ]
        )

        result = await self.chat_service.get_chat_history(session_id, customer_id)
        assert result["session_id"] == session_id
        assert result["message_count"] == 2
        assert len(result["messages"]) == 2


class TestChatServiceConversationContext:
    """Tests for conversation context management."""

    def setup_method(self):
        self.mock_supabase = MagicMock()
        self.chat_service = ChatService(self.mock_supabase)

    @pytest.mark.asyncio
    async def test_context_limited_to_20_messages(self):
        """Conversation context is limited to last 20 messages."""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Create 25 messages
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}", "created_at": now}
            for i in range(25)
        ]

        self.mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=messages
        )

        result = await self.chat_service._get_conversation_context(session_id)
        assert len(result) == 20
        # Should be the last 20 messages
        assert result[0]["content"] == "Message 5"
        assert result[-1]["content"] == "Message 24"

    @pytest.mark.asyncio
    async def test_context_preserves_chronological_order(self):
        """Messages are returned in chronological order."""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        messages = [
            {"role": "user", "content": "First", "created_at": now},
            {"role": "assistant", "content": "Second", "created_at": now},
            {"role": "user", "content": "Third", "created_at": now},
        ]

        self.mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=messages
        )

        result = await self.chat_service._get_conversation_context(session_id)
        assert len(result) == 3
        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Second"
        assert result[2]["content"] == "Third"


class TestChatServiceErrorHandling:
    """Tests for error handling in chat service."""

    def test_session_not_found_error(self):
        """SessionNotFoundError has correct status code."""
        error = SessionNotFoundError("test-id")
        assert error.status_code == 404
        assert "test-id" in error.message

    def test_session_limit_reached_error(self):
        """SessionLimitReachedError has correct status code."""
        error = SessionLimitReachedError("test-id")
        assert error.status_code == 400
        assert "20" in error.message

    def test_ai_service_unavailable_error(self):
        """AIServiceUnavailableError has correct status code and Vietnamese message."""
        error = AIServiceUnavailableError()
        assert error.status_code == 503
        assert "Dịch vụ AI tạm thời không khả dụng" in error.message
        assert "số điện thoại" in error.message


# ============================================================
# Schema Tests
# ============================================================


class TestChatSchemas:
    """Tests for chat Pydantic schemas."""

    def test_send_message_request_valid(self):
        """Valid message request."""
        from app.schemas.chat import SendMessageRequest

        req = SendMessageRequest(content="Xin chào")
        assert req.content == "Xin chào"

    def test_send_message_request_empty_content_rejected(self):
        """Empty content is rejected."""
        from app.schemas.chat import SendMessageRequest

        with pytest.raises(Exception):
            SendMessageRequest(content="")

    def test_send_message_request_too_long_rejected(self):
        """Content over 2000 chars is rejected."""
        from app.schemas.chat import SendMessageRequest

        with pytest.raises(Exception):
            SendMessageRequest(content="A" * 2001)

    def test_recommendation_item_schema(self):
        """RecommendationItem schema works correctly."""
        from app.schemas.chat import RecommendationItem

        item = RecommendationItem(
            product_name="Bánh Dâu",
            price=350000,
            reasoning="Phù hợp sinh nhật",
        )
        assert item.product_name == "Bánh Dâu"
        assert item.price == 350000

    def test_ai_summary_schema(self):
        """AISummary schema works correctly."""
        from app.schemas.chat import AISummary

        summary = AISummary(
            size="20cm",
            flavor="socola",
            decorations="hoa kem",
            pickup_date="2024-03-15",
            total_price=450000,
        )
        assert summary.size == "20cm"
        assert summary.total_price == 450000
