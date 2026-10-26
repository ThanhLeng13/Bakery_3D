"""Nguồn quyết định giá bánh tùy chỉnh — phía server.

Vì sao bảng giá nằm ở backend
-----------------------------
Trước đây có ba bảng tiền rời rạc: `BASE_PRICES` trong price-calculator.ts (Studio),
`SIZE_PRICES` trong checkout/page.tsx (chỉ theo size) và bảng trong chính file này.
Chúng lệch nhau, nên khách thấy 480.000đ ở Studio rồi bị tính 350.000đ — mất
130.000đ mỗi đơn có topping và trang trí.

Quyết định nghiệp vụ 07/10/2026: **server là nguồn quyết định duy nhất.** Server
tính đủ size + topping + trang trí; giao diện chỉ hiển thị con số server trả về,
không tự cộng.

Nếu muốn giao diện hiện giá trước khi lưu, hãy cho frontend gọi
`POST /api/v1/orders/quote` (chưa có) thay vì nhân bản bảng này sang TypeScript.
Nhân bản chính là nguồn của lỗi chênh giá.
"""

# Placeholder Cake Builder gửi thay cho product_id, vì bánh tùy chỉnh không có
# dòng trong bảng products.
NIL_UUID = "00000000-0000-0000-0000-000000000000"

# ── Bảng giá (VND) ───────────────────────────────────────────────────────────

CAKE_SIZE_PRICES: dict[str, int] = {
    "16cm": 250_000,
    "20cm": 350_000,
    "24cm": 450_000,
    "2-tier": 650_000,
}

CAKE_TOPPING_COSTS: dict[str, int] = {
    "flowers": 80_000,
    "fruits": 60_000,
    "chocolate drip": 50_000,
    "sprinkles": 30_000,
    "macarons": 100_000,
    "text": 40_000,
}

CAKE_DECORATION_COSTS: dict[str, int] = {
    "piping": 30_000,
    "rosettes": 50_000,
    "sprinkles": 20_000,
    "ribbon": 25_000,
    "pearls": 45_000,
}

# Khi khách không chọn kích cỡ, tính theo kích cỡ phổ biến nhất — khớp với
# fallback mà checkout từng dùng.
DEFAULT_CAKE_SIZE = "20cm"
DEFAULT_CAKE_PRICE = CAKE_SIZE_PRICES[DEFAULT_CAKE_SIZE]

TWO_TIER_SIZES = ("2-tier", "2 tier", "2tier")

# Giờ chuẩn bị tối thiểu (giờ) theo kích cỡ, khớp _validate_pickup_date.
SIZE_LEAD_HOURS: dict[str, int] = {
    "16cm": 24,
    "20cm": 24,
    "24cm": 24,
    "2-tier": 48,
}
DEFAULT_LEAD_HOURS = 24

# Ba vùng có thể trang trí, khớp CakeDesign.zones ở frontend.
ZONE_NAMES = ("top", "body", "border")


# ── Hàm dùng chung ───────────────────────────────────────────────────────────


def normalize_size(size) -> str:
    """Chuẩn hóa kích cỡ để tra bảng; '' nếu thiếu hoặc không dùng được."""
    if not isinstance(size, str):
        return ""
    return size.strip().lower()


def catalogue_product_id(item: dict):
    """ID sản phẩm DANH MỤC của một dòng đơn, hay None nếu là mẫu đặt.

    Đơn từ checkout gửi `product_id`; đơn từ trợ lý gửi `cake_id` — cùng một
    thứ, hai tên khác nhau. Trước đây hàm này chỉ đọc `product_id`, nên mọi dòng
    do trợ lý gửi đều bị coi là MẪU ĐẶT và bị bắt chờ 24 hay 48 giờ — tức là
    một chiếc bánh đã có sẵn trong danh mục bị từ chối đơn dù khách nhận ngay
    hôm nay.

    Trả về None khi không có id nào, vì lúc đó chưa biết là hàng danh mục hay
    mẫu đặt: mặc định là thận trọng hơn.
    """
    if not isinstance(item, dict):
        return None
    for key in ("product_id", "cake_id"):
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if not text or text == NIL_UUID:
            continue
        return text
    return None


def is_custom_cake(item) -> bool:
    """True khi món không có sản phẩm danh mục đứng sau.

    Nhận cả dòng đơn (dict) lẫn id trần, để nơi gọi không phải tự biết mình
    đang cầm cái gì.
    """
    if isinstance(item, dict):
        return catalogue_product_id(item) is None
    return item is None or str(item) == NIL_UUID


def is_two_tier(size) -> bool:
    """True khi kích cỡ là bánh hai tầng."""
    return normalize_size(size) in TWO_TIER_SIZES


def lead_hours_for_items(items) -> int:
    """Giờ chuấn bề tối thiểu của một đơn, theo kích cỡc khách chọn.

    Nguồn duy nhất cho cả hai nơi kiểm tra: agent (`order_tools`) và checkout
    (`order_service._validate_pickup_date`). Trước đây agent suy ra từ *tên*
    sản phẩm ("2 tḟng", "figure"...) còn checkout suy ra từ *kích cỡc*, nên
    cùng một đơn cho hai đáp án lệch nhau đúng 24 giờ — bánh tên "2 tḟng" nhưng
    khách chọn 20cm thì agent báo 48h trong khi chốt đơn chỉ cần 24h.

    Nhiều dòng trong `items` thì lấy mức cao nhất: một đơn có bánh hai tḟng vẫn
    cần 48h dù các dòng khác là bánh một tḟng.

    **Chỉ mẫu ĐẶT mới cần chờ.** Mẫu làm sẵn (có `product_id` thật trong
    danh mục) là hàng tiệm đã làm sẵn để bán cho khách chọn, nên bán liền được
    giống bán bất kỳ món nào khác — kể cả mẫu hai tḟng đã làm sẵn. Vì vậy dòng
    có `product_id` thật không tính vào mốc chờ.

    Trước đây mọi dòng đều bị tính, nên một chiếc bánh hai tḟng đã làm sẵn bị bắt
    phải đặt trước 48 giờ — sai, vì nó không cần làm gì cả.

    Trả về 0 nghĩa là "bán ngay": đơn chỉ gồm mẫu làm sẵn.
    """
    if not items:
        # Chưa biết khách chọn gì: dùng mức mặc định, thẬn trọng hơn.
        return DEFAULT_LEAD_HOURS

    longest = 0
    has_custom = False
    for item in items:
        if not isinstance(item, dict):
            continue
        # Mẫu làm sẵn trong danh mục: có sẵn, không cần chờ làm.
        if not is_custom_cake(item):
            continue
        has_custom = True
        size = item.get("size")
        # Mẫu đặt không có size: dùng mức mặc định.
        hours = SIZE_LEAD_HOURS.get(normalize_size(size), DEFAULT_LEAD_HOURS)
        longest = max(longest, hours)
    if has_custom:
        return longest
    # Toàn mẫu làm sẵn: bán ngay, không cần chờ.
    return 0


def custom_design_lead_hours(items) -> int:
    """Mốc chờ để được NHậN một mẫu ĐẶT (bánh tùy chỉnh).

    Khác `lead_hours_for_items`: hàm đó trả mốc chờ của đơn ĐANG CÓ — mẫu làm sẵn thì 0 giờ.
    Hàm này trả mốc mà khách phải đạt để tiệm nhận làm mẫu mới.

    Nếu đơn đang có chỉ mẫu làm sẵn thì chưa biết khách định đặt mẫu gì, nên
    lấy mức mặc định (24 giờ cho bánh đơn giản) — mức nhẹ nhất mà vẫn kệp.
    """
    longest = 0
    for item in items or []:
        if not isinstance(item, dict):
            continue
        if not is_custom_cake(item):
            continue
        hours = SIZE_LEAD_HOURS.get(
            normalize_size(item.get("size")), DEFAULT_LEAD_HOURS
        )
        longest = max(longest, hours)
    return longest or DEFAULT_LEAD_HOURS


def cake_price(size) -> int:
    """Giá của một chiếc bánh tùy chỉnh theo kích cỡ.

    Chỉ dùng cho nơi cần *một con số theo kích cỡ* (ví dụ ước lượng trước khi
    khách chọn topping). Khi khách đã cấu hình xong, dùng `price_breakdown` để
    lấy tổng thật.
    """
    return CAKE_SIZE_PRICES.get(normalize_size(size), DEFAULT_CAKE_PRICE)


def lead_hours(size) -> int:
    """Giờ chuẩn bị tối thiểu theo kích cỡ."""
    return SIZE_LEAD_HOURS.get(normalize_size(size), DEFAULT_LEAD_HOURS)


def _normalize_keys(items) -> set[str]:
    """Chuẩn hóa danh sách khoản đã chọn: bỏ trùng, bỏ rỗng, bỏ kiểu sai."""
    if not items:
        return set()
    if isinstance(items, str):
        items = [items]
    keys = set()
    for raw in items:
        if isinstance(raw, str) and raw.strip():
            keys.add(raw.strip().lower())
    return keys


def _decoration_cost(zones) -> int:
    """Cộng giá trang trí của cả ba vùng."""
    if not isinstance(zones, dict):
        return 0
    total = 0
    for zone in ZONE_NAMES:
        data = zones.get(zone)
        if not isinstance(data, dict):
            continue
        decoration = data.get("decoration")
        if not isinstance(decoration, str) or not decoration.strip():
            continue
        total += CAKE_DECORATION_COSTS.get(decoration.strip().lower(), 0)
    return total


def price_breakdown(design) -> dict:
    """Tính giá đầy đủ cho một cấu hình bánh.

    Khoản không có trong bảng giá được coi là 0 phí. Đây là chủ ý: bảng giá là
    cấu hình kinh doanh, thiếu một mục không được làm hỏng cả đơn hàng, và
    test_bang_topping_viend_co_bat_buoc canh giữ việc bảng không bị bỏ sót.

    Args:
        design: dict dạng CakeDesign của frontend — có `size`, `topping_type`
            và `zones` (top/body/border). Không bắt buộc đủ mọi khoá.

    Returns:
        dict gồm base_price, topping_cost, decoration_cost, total.

    Raises:
        ValueError: khi `size` có mặt nhưng không thuộc bảng giá. Thiếu `size`
            hoàn toàn thì dùng kích cỡ mặc định.
    """
    if not isinstance(design, dict):
        design = {}

    raw_size = design.get("size")
    if raw_size is None or (isinstance(raw_size, str) and not raw_size.strip()):
        base = DEFAULT_CAKE_PRICE
    else:
        key = normalize_size(raw_size)
        if key not in CAKE_SIZE_PRICES:
            raise ValueError(
                f"Kích cỡ bánh không hợp lệ: {raw_size!r}. "
                f"Chỉ nhận: {', '.join(sorted(CAKE_SIZE_PRICES))}."
            )
        base = CAKE_SIZE_PRICES[key]

    topping = sum(
        CAKE_TOPPING_COSTS.get(key, 0)
        for key in _normalize_keys(design.get("topping_type"))
    )
    decoration = _decoration_cost(design.get("zones"))

    return {
        "base_price": base,
        "topping_cost": topping,
        "decoration_cost": decoration,
        "total": base + topping + decoration,
    }


def order_total(design) -> int:
    """Tổng tiền một chiếc bánh tùy chỉnh, theo đúng thứ sẽ ghi vào đơn."""
    return price_breakdown(design)["total"]
