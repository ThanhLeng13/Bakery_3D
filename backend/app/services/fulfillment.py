"""Hình thức nhận bánh — khách GHÉ LẤY tại quán hay tiệm GIAO HÀNG tận nơi.

Bối cảnh
--------
Trước module này, đơn hàng chỉ có `pickup_date`, nên hai loại đơn khác nhau về
mặt vận hành lại được lưu giống hệt nhau:

    đơn ghé lấy  — thợ làm xong, để quầy, chờ khách tới
    đơn giao     — thợ làm xong, phải đóng gói và giao tới một địa chỉ

Thợ đọc đơn không phân biệt được, và trợ lý AI không có chỗ nào để hỏi "anh/chị
muốn ghé lấy hay giao hàng". Nhét địa chỉ vào `ai_summary` (tóm tắt cho thợ) sẽ
làm hỏng nghĩa của cả hai trường và không kiểm tra được độ dài.

Quy tắc ở đây là nguồn sự thật duy nhất cho cả API, trợ lý AI và CSDL:

    pickup   — địa chỉ PHẢI rỗng (không lưu hai nguồn mâu thuẫn)
    delivery — địa chỉ BẮT BUỘC, 10..300 ký tự sau khi bỏ khoảng trắng thừa
"""

from __future__ import annotations

from typing import Any

# Giá trị hợp lệ của `orders.fulfillment_type` (khớp CHECK trong migration
# `add_fulfillment_and_purchase_voucher.sql`).
FULFILLMENT_PICKUP = "pickup"
FULFILLMENT_DELIVERY = "delivery"
FULFILLMENT_TYPES = (FULFILLMENT_PICKUP, FULFILLMENT_DELIVERY)

MIN_ADDRESS_LENGTH = 10
MAX_ADDRESS_LENGTH = 300

# Cách khách và LLM hay viết. Chuẩn hoá trước khi so khớp để "Giao hàng",
# "delivery", "shipper" đều ra cùng một giá trị.
_DELIVERY_WORDS = (
    "delivery",
    "giao",
    "giao hang",
    "giao tận nơi",
    "giao tan noi",
    "shipper",
    "ship",
    "chuyen phat",
    "tận nơi",
    "tan noi",
)
_PICKUP_WORDS = (
    "pickup",
    "pick up",
    "ghe lay",
    "ghé lấy",
    "tu lay",
    "tự lấy",
    "den lay",
    "đến lấy",
    "lay tai quan",
    "lấy tại quán",
    "nhan tai quan",
    "nhận tại quán",
    "tai quan",
    "tại quán",
    "tu den",
    "tự đến",
)


class FulfillmentError(ValueError):
    """Hình thức nhận hàng hoặc địa chỉ không dùng được."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _fold(text: str) -> str:
    """Chữ thường, bỏ dấu, gộp khoảng trắng — để so khớp từ khoá.

    Khách gõ "Giao Hàng" hay "giao hang" đều phải ra cùng kết quả; nếu so khớp
    thô thì mỗi biến thể lại thành một trường hợp không ai xử lý.
    """
    import unicodedata

    lowered = str(text).strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    # "đ" không tách được bằng NFD, phải thay tay.
    stripped = stripped.replace("đ", "d")
    return " ".join(stripped.split())


def normalize_fulfillment_type(value: Any) -> str:
    """Đưa giá trị bất kỳ của khách/LLM về 'pickup' hoặc 'delivery'.

    Rỗng → 'pickup'. Đây là mặc định có chủ ý: đa số khách của tiệm ghé lấy, và
    chọn 'delivery' mà thiếu địa chỉ sẽ tạo ra đơn không giao được.

    Giá trị lạ thì NÉM LỖI, không đoán. Đoán bừa một chuỗi lạ thành 'delivery'
    có thể biến đơn ghé lấy thành đơn giao hàng mà không ai biết.
    """
    if value is None:
        return FULFILLMENT_PICKUP

    folded = _fold(value)
    if not folded:
        return FULFILLMENT_PICKUP

    if folded in FULFILLMENT_TYPES:
        return folded

    # Xét "giao" trước "lấy": câu "giao hàng chứ không ghé lấy" có cả hai từ,
    # nhưng ý khách là giao hàng.
    if any(word in folded for word in _DELIVERY_WORDS):
        return FULFILLMENT_DELIVERY
    if any(word in folded for word in _PICKUP_WORDS):
        return FULFILLMENT_PICKUP

    raise FulfillmentError(
        f"Không hiểu hình thức nhận hàng '{value}'. "
        "Chỉ có 'pickup' (ghé lấy tại quán) hoặc 'delivery' (giao hàng)."
    )


def normalize_address(value: Any) -> str | None:
    """Bỏ khoảng trắng thừa; rỗng thành None."""
    if value is None:
        return None
    clean = " ".join(str(value).split())
    return clean or None


def resolve_fulfillment(
    fulfillment_type: Any = None,
    delivery_address: Any = None,
) -> dict:
    """Chuẩn hoá và kiểm tra cặp (hình thức nhận, địa chỉ).

    Trả về `{"fulfillment_type": str, "delivery_address": str | None}`.

    Raises:
        FulfillmentError: hình thức không hiểu được, hoặc giao hàng mà thiếu
            địa chỉ, hoặc ghé lấy mà lại kèm địa chỉ.
    """
    kind = normalize_fulfillment_type(fulfillment_type)
    address = normalize_address(delivery_address)

    if kind == FULFILLMENT_DELIVERY:
        if address is None:
            raise FulfillmentError(
                "Đơn giao hàng cần địa chỉ nhận cụ thể. "
                "Hãy hỏi khách địa chỉ giao tới trước khi chốt đơn."
            )
        if len(address) < MIN_ADDRESS_LENGTH:
            raise FulfillmentError(
                f"Địa chỉ giao hàng quá ngắn (cần ít nhất "
                f"{MIN_ADDRESS_LENGTH} ký tự, ví dụ số nhà và tên đường)."
            )
        if len(address) > MAX_ADDRESS_LENGTH:
            raise FulfillmentError(
                f"Địa chỉ giao hàng quá dài (tối đa {MAX_ADDRESS_LENGTH} ký tự)."
            )
        return {"fulfillment_type": FULFILLMENT_DELIVERY, "delivery_address": address}

    # Ghé lấy tại quán: địa chỉ giao hàng vô nghĩa, bỏ hẳn. Giữ lại sẽ thành
    # hai nguồn sự thật: `fulfillment_type` nói ghé lấy nhưng vẫn có địa chỉ,
    # và thợ không biết tin cái nào.
    return {"fulfillment_type": FULFILLMENT_PICKUP, "delivery_address": None}
