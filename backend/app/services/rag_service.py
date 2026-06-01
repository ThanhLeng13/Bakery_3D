"""RAG (Retrieval-Augmented Generation) service for AI chatbot.

Handles:
- Product catalog querying and filtering
- Context building for Claude API prompts
- System prompt construction with Vietnamese language rules
"""

import json
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Bạn là tư vấn viên bánh kem chuyên nghiệp tại tiệm bánh Bơ Nơ, TP.HCM.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Chỉ gợi ý sản phẩm có trong danh mục
- Bao gồm giá chính xác từ danh mục
- Hỏi thêm nếu thông tin chưa đủ (dịp, số người, ngân sách)
- Tối đa 5 gợi ý mỗi lần
- Khi khách xác nhận, tạo AI_Summary dạng JSON

Khi gợi ý sản phẩm, trả lời theo format:
- Tên sản phẩm, giá, lý do phù hợp

Khi khách hàng xác nhận đặt hàng, tạo AI_Summary JSON với format:
```json
{{
  "size": "kích thước bánh",
  "flavor": "hương vị",
  "decorations": "trang trí",
  "pickup_date": "ngày nhận",
  "total_price": giá_số
}}
```

Nếu không tìm thấy sản phẩm phù hợp, hãy gợi ý các lựa chọn gần nhất hoặc hỏi khách điều chỉnh tiêu chí.

Nếu thông tin khách hàng chưa đủ (thiếu dịp, kích thước, hoặc ngân sách), hãy hỏi thêm trước khi gợi ý.

Danh mục sản phẩm hiện có:
{product_catalog_json}"""


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

    def build_system_prompt(self, product_catalog_json: str) -> str:
        """
        Build the system prompt with product catalog context.

        Args:
            product_catalog_json: Formatted JSON string of product catalog

        Returns:
            Complete system prompt string
        """
        return SYSTEM_PROMPT_TEMPLATE.format(
            product_catalog_json=product_catalog_json
        )

    async def build_context(
        self,
        occasion: Optional[str] = None,
        budget: Optional[int] = None,
        size: Optional[str] = None,
    ) -> str:
        """
        Build complete RAG context: fetch products, filter, format, and create system prompt.

        Args:
            occasion: Optional occasion filter
            budget: Optional budget filter
            size: Optional size filter

        Returns:
            Complete system prompt with product catalog context
        """
        # Fetch all active products
        products = await self.get_product_catalog()

        # Filter by criteria if any provided
        if occasion or budget or size:
            products = await self.filter_products_by_criteria(
                products, occasion=occasion, budget=budget, size=size
            )

        # Format catalog as JSON context
        catalog_json = self.format_catalog_context(products)

        # Build and return system prompt
        return self.build_system_prompt(catalog_json)
