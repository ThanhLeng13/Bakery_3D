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
)
from app.services.order_tools import dispatch
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

    def test_build_system_prompt_has_shop_identity(self):
        """Prompt neu dung thong tin tiem va gio mo cua."""
        result = self.rag_service.build_system_prompt()

        assert "Bơ Nơ" in result
        assert "Đà Nẵng" in result
        assert "tiếng Việt" in result

    def test_build_system_prompt_contains_rules(self):
        """System prompt chua cac quy tac bat buoc cua tro ly dat banh.

        Doi tu bo cuc cu: prompt gio KHONG con nhoi danh muc san pham va khong con
        bat LLM tu viet AI_Summary JSON. Thay vao do no cam LLM bia gia/ten banh va
        bat phai dung cong cu.
        """
        result = self.rag_service.build_system_prompt()

        assert "Luôn trả lời bằng tiếng Việt" in result
        # Quy tac quan trong nhat: khong duoc bia.
        assert "KHÔNG bao giờ tự nghĩ ra giá" in result
        assert "KHÔNG bao giờ tự nghĩ ra tên bánh" in result
        # Phai tra cuu bang cong cu.
        assert "find_cakes" in result
        assert "check_bake_time" in result
        assert "create_draft_order" in result

    def test_prompt_does_not_embed_product_catalog(self):
        """Danh muc KHONG con nhồi vao prompt.

        Truoc day ca danh muc duoc do vao prompt, khien prompt phinh theo so luong
        san pham va ten/gia do LLM nho lai. Gio tra qua cong cu.
        """
        result = self.rag_service.build_system_prompt()
        assert "{product_catalog_json}" not in result
        # Khong con cho nao de danh muc JSON lot vao.
        assert "Danh mục sản phẩm hiện có" not in result


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
# Ordering agent tests
#
# Thay cho cac test boc regex cu. Cach cu bat LLM viet JSON trong cau tra loi roi
# dung regex lay lai — de bia gia va vo khi LLM doi cach trinh bay. Gio gia va ten
# banh do CONG CU doc tu CSDL tra ve, nen test tap trung vao lop cong cu.
# ============================================================


def _fake_products():
    """Kho gia de test, khong goi mang."""
    return [
        {"id": "id-hoa", "name": "Bánh kem hoa hồng đỏ", "description": "Hoa hồng đỏ",
         "category": "sinh nhật", "base_price": 430000, "sizes": ["20cm"],
         "flavors": ["vanilla"], "product_type": "cake"},
        {"id": "id-2tang", "name": "Bánh kem 2 tầng hoa hồng phấn", "description": "2 tầng",
         "category": "cưới", "base_price": 690000, "sizes": ["25cm"],
         "flavors": ["socola"], "product_type": "cake"},
        {"id": "id-re", "name": "Bánh kem chữ Happy Birthday", "description": "Đơn giản",
         "category": "sinh nhật", "base_price": 170000, "sizes": ["18cm"],
         "flavors": ["vanilla"], "product_type": "cake"},
    ]


def _tools():
    from app.services.order_tools import OrderTools

    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=_fake_products())
    )
    return OrderTools(client)


def _pickup_in(days):
    from datetime import datetime, timedelta

    from app.services.order_tools import VN_TZ

    return (datetime.now(VN_TZ) + timedelta(days=days)).strftime("%Y-%m-%d")


class TestOrderToolsFindCakes:
    """find_cakes tra ve du lieu THAT tu kho, khong do LLM nghi ra."""

    def test_filters_by_budget(self):
        result = _tools().find_cakes(budget=200000)
        assert result["found"] == 1
        assert result["cakes"][0]["name"] == "Bánh kem chữ Happy Birthday"
        assert result["cakes"][0]["price"] == 170000

    def test_over_budget_suggests_cheapest(self):
        """Ngan sach qua thap: goi y mau re nhat thay vi tra rong."""
        result = _tools().find_cakes(budget=50000)
        assert result["found"] == 0
        assert result["suggestions"][0]["price"] == 170000

    def test_rejects_non_numeric_budget(self):
        from app.services.order_tools import ToolError

        with pytest.raises(ToolError):
            _tools().find_cakes(budget="nhiều")

    def test_results_center_on_budget_not_cheapest(self):
        """'Ngan sach khoang 450k' nghia la muon chi co 450k, khong phai re nhat.

        Do thuc te: neu chi lay gia tang dan thi mau 170k luon dung dau va tro ly
        chi goi y banh re nhat, du khach noi ro muc tien.
        """
        result = _tools().find_cakes(budget=430000)
        prices = [c["price"] for c in result["cakes"]]
        # 430k phai dung dau (gan ngan sach nhat), khong phai 170k.
        assert prices[0] == 430000, f"phai uu tien gan ngan sach, nhan duoc {prices}"

    def test_keyword_still_wins_over_budget_proximity(self):
        """Co tu khoa thi uu tien dung mo ta, khong phai gan ngan sach."""
        result = _tools().find_cakes(budget=430000, keyword="Happy Birthday")
        assert "Happy Birthday" in result["cakes"][0]["name"]

    def test_ignores_generic_keywords(self):
        """Tu chung chung nhu 'banh', 'kem' khong duoc tinh la khop.

        Do thuc te: truoc khi loc, tu khoa 'Bánh kem chữ Chúc Mừng' khop 91/105
        banh — tra ve gan nhu ca kho nen vo dung.
        """
        result = _tools().find_cakes(keyword="Bánh kem")
        # Khong tu nao con lai la tu khoa that -> tra ve TAT CA (khong loc),
        # chu khong phai tra ve rac.
        assert result["found"] == 3

    def test_complex_cake_needs_longer_lead(self):
        """Banh nhieu tang phai can dat truoc lau hon banh thuong."""
        result = _tools().find_cakes(keyword="2 tầng")
        two_tier = next(c for c in result["cakes"] if "2 tầng" in c["name"])
        assert two_tier["needs_lead_hours"] == 48


class TestOrderToolsPriceOrder:
    """Gia LUON lay tu CSDL — diem quan trong nhat cua lop cong cu."""

    def test_ignores_price_claimed_by_llm(self):
        """LLM khai gia sai thi van dung gia trong kho."""
        result = _tools().price_order(
            items=[{"name": "Bánh kem hoa hồng đỏ", "quantity": 2, "unit_price": 1}]
        )
        assert result["items"][0]["unit_price"] == 430000, "phai dung gia CSDL"
        assert result["total_price"] == 860000

    def test_flags_over_budget(self):
        result = _tools().price_order(
            items=[{"name": "Bánh kem hoa hồng đỏ", "quantity": 1}], budget=100000
        )
        assert result["over_budget"] is True
        assert result["difference"] == 330000

    def test_unknown_cake_is_rejected(self):
        from app.services.order_tools import ToolError

        with pytest.raises(ToolError):
            _tools().price_order(items=[{"name": "Bánh Không Tồn Tại", "quantity": 1}])

    def test_rejects_bad_quantity(self):
        from app.services.order_tools import ToolError

        with pytest.raises(ToolError):
            _tools().price_order(items=[{"name": "Bánh kem hoa hồng đỏ", "quantity": 0}])


class TestOrderToolsBakeTime:
    """Kiem tra thoi gian — truoc day LLM tu hua ngay voi khach."""

    def test_rejects_too_soon(self):
        """Hom nay thi khong kip (can 24h)."""
        from app.services.order_tools import VN_TZ
        from datetime import datetime

        today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
        result = _tools().check_bake_time(today)
        assert result["is_possible"] is False
        # So gio khong duoc am — truoc day tra -10 gio trong rat vo ly.
        assert result["hours_notice"] >= 0

    def test_accepts_far_future(self):
        assert _tools().check_bake_time(_pickup_in(10))["is_possible"] is True

    def test_rejects_unparseable_date(self):
        from app.services.order_tools import ToolError

        with pytest.raises(ToolError):
            _tools().check_bake_time("ngày mai")


class TestOrderToolsDispatch:
    """dispatch phai bao loi MEM de LLM doc va sua, khong lam sap request."""

    def test_unknown_tool(self):
        assert "error" in dispatch(_tools(), "khong_co", {})

    def test_bad_arguments(self):
        assert "error" in dispatch(_tools(), "get_cake_detail", {})

    def test_bad_json_is_reported(self):
        assert "error" in dispatch(_tools(), "find_cakes", {"budget": "nhiều"})

    def test_missing_customer_blocks_order(self):
        """Thieu customer_id thi KHONG tao don (cot customer_id la NOT NULL)."""
        result = dispatch(_tools(), "create_draft_order", {
            "customer_name": "Khách", "customer_phone": "0901234567",
            "pickup_date": _pickup_in(5),
            "items": [{"name": "Bánh kem hoa hồng đỏ", "quantity": 1}],
        })
        assert result["created"] is False
        assert result["reason"] == "not_logged_in"

    def test_accepts_alias_parameter_names(self):
        """LLM goi 'phone' thay vi 'customer_phone' van phai hieu.

        Da gap that: model goi create_draft_order voi 'phone', ham nem TypeError,
        model thu lai va dot het 4 vong ma khong tao duoc don.
        """
        from app.services.order_tools import _normalize_arguments

        out = _normalize_arguments("create_draft_order", {
            "name": "Khách", "phone": "0901234567", "date": _pickup_in(5),
            "cakes": [{"name": "Bánh kem hoa hồng đỏ", "quantity": 1}],
        })
        assert out["customer_name"] == "Khách"
        assert out["customer_phone"] == "0901234567"
        assert out["pickup_date"] == _pickup_in(5)
        assert "items" in out

    def test_alias_does_not_overwrite_correct_param(self):
        """Ten dung da co thi giu nguyen, khong de ten sai ghi de."""
        from app.services.order_tools import _normalize_arguments

        out = _normalize_arguments("price_order", {
            "items": [{"name": "A", "quantity": 1}], "cakes": [{"name": "B", "quantity": 9}],
        })
        assert out["items"][0]["name"] == "A"

    def test_bad_params_tell_llm_the_right_names(self):
        """Loi tham so phai noi ro ten dung, de LLM sua ngay vong sau."""
        result = dispatch(_tools(), "price_order", {"khong_co_gi": 1})
        assert "error" in result
        assert "expected_parameters" in result
        assert "items" in result["expected_parameters"]


class TestToolSchemas:
    """Khai bao cong cu phai dung chuan Groq, neu khong API se tu choi."""

    def test_every_tool_has_name_and_description(self):
        from app.services.order_tools import TOOL_SCHEMAS

        for tool in TOOL_SCHEMAS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert fn["name"] and fn["description"]
            assert fn["parameters"]["type"] == "object"

    def test_every_declared_tool_has_a_handler(self):
        """Moi cong cu khai bao voi Groq phai co ham xu ly tuong ung."""
        from app.services.order_tools import TOOL_SCHEMAS, OrderTools

        for tool in TOOL_SCHEMAS:
            name = tool["function"]["name"]
            assert hasattr(OrderTools, name), f"thieu ham xu ly cho '{name}'"


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
