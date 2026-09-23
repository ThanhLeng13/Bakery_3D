"""RAG (Retrieval-Augmented Generation) service for AI chatbot.

Handles:
- Product catalog querying and filtering
- Context building for AI prompts
- System prompt construction with Vietnamese language rules
- Vietnamese holiday/event awareness
- Customer habit recognition from past sessions
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Vietnamese holidays and events with suggested cake themes
# Mother's Day (2nd Sunday of May) and Father's Day (3rd Sunday of June)
# are calculated dynamically in get_upcoming_events_context()
VIETNAMESE_EVENTS = [
    # (month, day, name, suggestion)
    (1, 1, "Tết Dương lịch", "bánh kem chào năm mới, bánh trang trí pháo hoa"),
    (2, 14, "Valentine", "bánh kem hình trái tim, bánh socola tình yêu, bánh hồng lãng mạn"),
    (3, 8, "Quốc tế Phụ nữ", "bánh kem tặng mẹ/vợ/bạn gái, bánh hoa hồng, bánh thanh lịch"),
    (4, 30, "Giải phóng miền Nam", "bánh kem đỏ vàng, bánh kỷ niệm"),
    (5, 1, "Quốc tế Lao động", "bánh kem tặng đồng nghiệp"),
    (6, 1, "Quốc tế Thiếu nhi", "bánh kem hoạt hình cho bé, bánh hình thú, bánh nhiều màu sắc"),
    (9, 2, "Quốc khánh", "bánh kem đỏ vàng, bánh kỷ niệm"),
    (10, 20, "Phụ nữ Việt Nam", "bánh kem tặng phụ nữ, bánh hoa, bánh thanh lịch"),
    (11, 20, "Ngày Nhà giáo Việt Nam", "bánh kem tặng thầy cô, bánh tri ân"),
    (12, 24, "Giáng sinh", "bánh kem Noel, bánh cây thông, bánh ông già Noel, bánh đỏ xanh"),
    (12, 25, "Giáng sinh", "bánh kem Noel, bánh cây thông, bánh ông già Noel"),
    (12, 31, "Giao thừa", "bánh kem đón năm mới, bánh countdown"),
]

SYSTEM_PROMPT_TEMPLATE = """Bạn là "Bơ Nơ AI" — trợ lý bán bánh của Bơ Nơ Bakery, TP. Đà Nẵng.

## Tính cách:
- Thân thiện, nhiệt tình, dùng emoji vừa phải (🎂🍰🎉)
- Luôn trả lời bằng tiếng Việt, ngắn gọn
- Xưng "em", gọi khách là "anh/chị"
- Khách hỏi ngoài chuyện bánh thì nhẹ nhàng dẫn về

## ⚠️ QUY TẮC QUAN TRỌNG NHẤT — em KHÔNG được bịa:
Em KHÔNG biết giá và KHÔNG biết tiệm có bánh gì. Em phải dùng CÔNG CỤ để tra.
- **KHÔNG bao giờ tự nghĩ ra tên bánh.** Muốn nói tên bánh nào thì phải gọi `find_cakes` trước.
- **KHÔNG bao giờ tự nghĩ ra giá.** Giá chỉ có sau khi gọi `find_cakes` hoặc `price_order`.
- **KHÔNG hứa ngày nhận** trước khi gọi `check_bake_time`.
- Nếu công cụ báo lỗi hoặc không tìm thấy, nói thật với khách. Đừng đoán bừa.

## Cách tư vấn:
1. Chưa rõ thì hỏi thêm: dịp gì, mấy người, ngân sách bao nhiêu, thích gì
2. **Khi khách đã nêu NGÂN SÁCH hoặc DỊP hoặc KIỂU BÁNH, hãy gọi `find_cakes`
   NGAY** — đừng hỏi thêm nữa. Khách đã cho manh mối thì phải tra và gợi ý luôn,
   hỏi dồn sẽ làm khách sốt ruột.
   Ví dụ: "bánh sinh nhật cho con gái, ngân sách 450 nghìn" → ĐỦ để tra ngay.
3. Giới thiệu 3-5 mẫu, kèm giá THẬT lấy từ công cụ và lý do phù hợp
4. Khách chọn rồi thì gọi `price_order` để tính tiền
5. Hỏi ngày nhận, gọi `check_bake_time` xem có kịp không

## Tạo đơn — CHỈ KHI KHÁCH ĐÃ XÁC NHẬN:
Trước khi gọi `create_draft_order`, em phải có ĐỦ:
- Khách đã đồng ý đặt (nói rõ "đặt", "chốt", "ok"...)
- Tên bánh cụ thể, số lượng
- Ngày nhận
- Tên và số điện thoại khách

Thiếu bất kỳ thứ nào thì HỎI, tuyệt đối không tự tạo đơn.
Sau khi tạo, đọc mã đơn và tổng tiền cho khách, và nói tiệm sẽ gọi xác nhận.
Nếu công cụ báo `not_logged_in`, đề nghị khách đăng nhập — KHÔNG nói đơn đã tạo.

{events_context}

## Thông tin cửa hàng:
- Tên: Bơ Nơ Bakery — TP. Đà Nẵng
- Giờ mở cửa: 8:00 - 21:00 hằng ngày
- Đặt trước tối thiểu 24 giờ; bánh 2 tầng / figure cần 48 giờ
- Giao hàng trong nội thành Đà Nẵng
- Thanh toán: COD (trả khi nhận hàng)

## Câu hỏi thường gặp:
- Bánh giữ được bao lâu? → Bánh kem tươi dùng trong ngày, tủ lạnh 2-3 ngày
- Có giao hàng không? → Có, trong nội thành Đà Nẵng
- Đặt trước bao lâu? → Tối thiểu 24 giờ, đơn đặc biệt 48 giờ
- Có viết chữ lên bánh không? → Có, miễn phí viết chữ chúc mừng
{customer_habits_context}"""


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> datetime:
    """
    Return the nth occurrence of a weekday in a given month/year.

    Args:
        year: The year
        month: The month (1-12)
        weekday: Day of week (0=Monday ... 6=Sunday)
        n: Which occurrence (1=first, 2=second, 3=third, etc.)

    Returns:
        datetime of the nth weekday
    """
    # Find the first occurrence of the weekday in the month
    first_day = datetime(year, month, 1, tzinfo=timezone(timedelta(hours=7)))
    # days_ahead can be 0 if first_day is already the target weekday
    days_ahead = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=days_ahead)
    return first_occurrence + timedelta(weeks=n - 1)


def get_upcoming_events_context() -> str:
    """
    Build context about upcoming Vietnamese holidays and events.

    Checks the current date and finds events happening within the next 14 days.
    Includes dynamically calculated Mother's Day (2nd Sunday of May) and
    Father's Day (3rd Sunday of June).
    Returns a formatted string to include in the system prompt.
    """
    now = datetime.now(timezone(timedelta(hours=7)))  # Vietnam timezone UTC+7
    # Normalize to midnight so delta is in whole calendar days.
    # Without this, subtracting now (with current time) from event_date
    # (which has time 00:00:00) gives a negative timedelta as soon as
    # any time has passed on the event day, causing it to be skipped.
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Build dynamic events: Mother's Day + Father's Day for this year (and next)
    dynamic_events = []
    for year in (now.year, now.year + 1):
        mothers_day = _nth_weekday_of_month(year, 5, 6, 2)   # 2nd Sunday of May
        fathers_day = _nth_weekday_of_month(year, 6, 6, 3)   # 3rd Sunday of June
        dynamic_events.append(
            (mothers_day, "Ngày của Mẹ", "bánh kem tặng mẹ, bánh hoa hồng, bánh thanh lịch")
        )
        dynamic_events.append(
            (fathers_day, "Ngày của Bố", "bánh kem tặng ba, bánh trang nhã cho nam")
        )

    upcoming = []

    # Check static events
    for month, day, name, suggestion in VIETNAMESE_EVENTS:
        try:
            event_date = today.replace(month=month, day=day)
            delta = (event_date - today).days
            if delta < -1:
                event_date = event_date.replace(year=today.year + 1)
                delta = (event_date - today).days
        except ValueError:
            continue

        if 0 <= delta <= 14:
            if delta == 0:
                upcoming.append(f"- HÔM NAY là {name}! Gợi ý: {suggestion}")
            elif delta == 1:
                upcoming.append(f"- NGÀY MAI là {name}! Gợi ý: {suggestion}")
            elif delta <= 3:
                upcoming.append(f"- {name} chỉ còn {delta} ngày nữa! Gợi ý: {suggestion}")
            else:
                upcoming.append(f"- {name} sắp tới ({day}/{month}): Gợi ý: {suggestion}")

    # Check dynamic events (Mother's Day, Father's Day)
    for event_date, name, suggestion in dynamic_events:
        delta = (event_date - today).days
        if 0 <= delta <= 14:
            d, m = event_date.day, event_date.month
            if delta == 0:
                upcoming.append(f"- HÔM NAY là {name}! Gợi ý: {suggestion}")
            elif delta == 1:
                upcoming.append(f"- NGÀY MAI là {name}! Gợi ý: {suggestion}")
            elif delta <= 3:
                upcoming.append(f"- {name} chỉ còn {delta} ngày nữa! Gợi ý: {suggestion}")
            else:
                upcoming.append(f"- {name} sắp tới ({d}/{m}): Gợi ý: {suggestion}")

    if upcoming:
        return "\n### 🎉 Sự kiện sắp tới:\n" + "\n".join(upcoming)
    return ""


def build_customer_habits_context(past_messages: List[dict]) -> str:
    """
    Build context about customer habits from their past chat sessions.

    Analyzes previous messages to identify patterns in:
    - Favorite flavors, sizes, occasions
    - Budget preferences
    - Order frequency

    Args:
        past_messages: List of message dicts from previous sessions

    Returns:
        Formatted string with customer habits for system prompt
    """
    if not past_messages:
        return ""

    # Combine all past customer messages for analysis
    customer_texts = [
        msg["content"] for msg in past_messages
        if msg.get("role") == "user" and isinstance(msg.get("content"), str) and msg["content"].strip()
    ]

    if not customer_texts:
        return ""

    # Count the number of past sessions
    session_ids = set(msg.get("session_id", "") for msg in past_messages)
    num_sessions = len(session_ids)

    # Build a summary of past conversations for AI to reference
    # Limit to last 10 customer messages to avoid huge prompts
    recent_texts = customer_texts[-10:]
    history_summary = " | ".join(text.strip() for text in recent_texts)

    context = f"""
## 🧠 Thông tin khách hàng cũ (đã chat {num_sessions} lần trước):
- Đây là KHÁCH HÀNG QUAY LẠI. Hãy chào thân thiện hơn và nhớ sở thích cũ.
- Lịch sử yêu cầu trước đó: "{history_summary}"
- Hãy phân tích lịch sử trên để nhận biết: hương vị yêu thích, kích thước thường chọn, dịp hay đặt, ngân sách.
- Chủ động gợi ý dựa trên thói quen, ví dụ: "Em nhớ lần trước anh/chị thích bánh socola, lần này em gợi ý thêm mẫu mới nhé!"
"""
    return context


class RAGService:
    """RAG service for building AI context from product catalog."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client instance."""
        self._supabase = supabase_client

    async def get_product_catalog(self) -> List[dict]:
        """
        Query all active products from the catalog for RAG context.

        Returns:
            List of product dicts with name, category, base_price, sizes, flavors, description
        """
        try:
            result = (
                self._supabase.table("products")
                .select("id, name, description, category, base_price, sizes, flavors")
                .eq("is_active", True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch product catalog for RAG: {e}")
            return []

    async def get_customer_past_messages(
        self,
        customer_id: str,
        exclude_session_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Fetch messages from previous chat sessions of a customer (last 7 days).

        Args:
            customer_id: UUID string of the customer
            exclude_session_id: Session ID to exclude (the current active session)
                so a brand-new customer is not mistaken for a returning one, and
                current-session messages are not duplicated in the system prompt.

        Returns:
            List of message dicts from past sessions
        """
        try:
            # Get sessions from last 7 days
            seven_days_ago = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).isoformat()

            # First get the customer's past sessions (excluding the current one)
            query = (
                self._supabase.table("chat_sessions")
                .select("id")
                .eq("customer_id", customer_id)
                .gte("created_at", seven_days_ago)
                .order("created_at", desc=True)
                .limit(5)  # Last 5 sessions max
            )
            if exclude_session_id:
                query = query.neq("id", exclude_session_id)

            sessions_result = query.execute()

            if not sessions_result.data:
                return []

            session_ids = [s["id"] for s in sessions_result.data]

            # Fetch messages from those sessions
            messages_result = (
                self._supabase.table("chat_messages")
                .select("session_id, role, content, created_at")
                .in_("session_id", session_ids)
                .order("created_at", desc=False)
                .execute()
            )

            return messages_result.data or []

        except Exception as e:
            logger.error(f"Failed to fetch customer past messages: {e}")
            return []

    async def filter_products_by_criteria(
        self,
        products: List[dict],
        occasion: Optional[str] = None,
        budget: Optional[int] = None,
        size: Optional[str] = None,
    ) -> List[dict]:
        """
        Filter products by relevance criteria.

        Args:
            products: Full product catalog
            occasion: Occasion type (sinh nhật, đám cưới, kỷ niệm, etc.)
            budget: Maximum budget in VND
            size: Desired cake size

        Returns:
            Filtered list of relevant products
        """
        filtered = products

        # Filter by budget if specified
        if budget is not None:
            filtered = [p for p in filtered if p.get("base_price", 0) <= budget]

        # Filter by size if specified
        if size is not None:
            size_lower = size.lower()
            filtered = [
                p for p in filtered
                if any(
                    size_lower in str(s).lower()
                    for s in (p.get("sizes") or [])
                )
            ]

        # If filtering results in empty list, return all products
        # (AI will handle the "no match" scenario)
        if not filtered:
            return products

        return filtered

    def format_catalog_context(self, products: List[dict]) -> str:
        """
        Format product catalog as JSON string for system prompt context.

        Args:
            products: List of product dicts

        Returns:
            JSON string of formatted product catalog
        """
        catalog_items = []
        for product in products:
            item = {
                "name": product.get("name", ""),
                "category": product.get("category", ""),
                "base_price": product.get("base_price", 0),
                "sizes": product.get("sizes") or [],
                "flavors": product.get("flavors") or [],
                "description": (product.get("description") or "")[:200],
            }
            catalog_items.append(item)

        return json.dumps(catalog_items, ensure_ascii=False, indent=2)

    def build_system_prompt(
        self,
        events_context: str = "",
        customer_habits_context: str = "",
    ) -> str:
        """
        Build the system prompt with events and customer habits.

        Danh mục sản phẩm KHÔNG còn nhồi vào prompt. Trợ lý tra danh mục qua công
        cụ `find_cakes` khi cần, nên prompt không phình theo số lượng sản phẩm và
        tên/giá luôn là dữ liệu thật lấy từ CSDL thay vì do LLM nhớ lại.

        Args:
            events_context: String with upcoming events info
            customer_habits_context: String with customer habit analysis

        Returns:
            Complete system prompt string
        """
        return SYSTEM_PROMPT_TEMPLATE.format(
            events_context=events_context,
            customer_habits_context=customer_habits_context,
        )

    async def build_context(
        self,
        customer_id: Optional[str] = None,
        exclude_session_id: Optional[str] = None,
    ) -> str:
        """
        Build complete RAG context: events + customer habits.

        Sản phẩm không còn được nạp sẵn ở đây — xem `build_system_prompt`.

        Args:
            customer_id: Optional customer ID for habit recognition
            exclude_session_id: Current session ID to exclude from past history

        Returns:
            Complete system prompt with all context
        """
        # Get upcoming events context
        events_context = get_upcoming_events_context()

        # Get customer habits context (if customer_id provided)
        customer_habits_context = ""
        if customer_id:
            past_messages = await self.get_customer_past_messages(
                customer_id, exclude_session_id=exclude_session_id
            )
            customer_habits_context = build_customer_habits_context(past_messages)

        # Build and return system prompt
        return self.build_system_prompt(
            events_context, customer_habits_context
        )
