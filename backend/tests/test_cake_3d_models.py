"""Tests for the public reusable 3D cake-model warehouse."""

from unittest.mock import MagicMock

import pytest

from app.services.cake_3d_model_service import (
    Cake3DModelNotFoundError,
    Cake3DModelService,
)


class MockQuery:
    def __init__(self, data=None, count=None, error=None, returns_none=False):
        self.data = data
        self.count = count
        self.error = error
        # `maybe_single()` của supabase-py trả về None khi không có dòng nào khớp,
        # chứ không phải object có .data = None.
        self.returns_none = returns_none
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args):
        self.filters.append(("eq", *args))
        return self

    def contains(self, *args):
        self.filters.append(("contains", *args))
        return self

    def order(self, *args, **kwargs):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if self.error:
            raise self.error
        if self.returns_none:
            return None
        result = MagicMock()
        result.data = self.data
        result.count = self.count
        return result


def test_list_models_returns_only_active_models_and_total():
    client = MagicMock()
    query = MockQuery(data=[{"slug": "heart-1-tier"}], count=1)
    client.table.return_value = query

    result = Cake3DModelService(client).list_models(category="birthday", tag="heart")

    assert result == {"models": [{"slug": "heart-1-tier"}], "total": 1}
    assert ("eq", "is_active", True) in query.filters
    assert ("eq", "category", "birthday") in query.filters
    assert ("contains", "tags", ["heart"]) in query.filters


def test_list_models_uses_row_count_when_postgrest_does_not_return_count():
    client = MagicMock()
    client.table.return_value = MockQuery(data=[{"slug": "round-1-tier"}], count=None)

    assert Cake3DModelService(client).list_models()["total"] == 1


def test_get_model_falls_back_from_uuid_lookup_to_slug():
    client = MagicMock()
    uuid_query = MockQuery(error=RuntimeError("invalid uuid"))
    slug_query = MockQuery(data={"slug": "heart-1-tier"})
    client.table.side_effect = [uuid_query, slug_query]

    result = Cake3DModelService(client).get_model("heart-1-tier")

    assert result["slug"] == "heart-1-tier"
    assert ("eq", "slug", "heart-1-tier") in slug_query.filters


def test_get_model_returns_not_found_for_missing_active_model():
    client = MagicMock()
    client.table.side_effect = [MockQuery(data=None), MockQuery(data=None)]

    with pytest.raises(Cake3DModelNotFoundError):
        Cake3DModelService(client).get_model("missing-model")


def test_get_model_treats_none_from_maybe_single_as_not_found():
    """Không có dòng nào -> 404, KHÔNG phải 500.

    Lỗi thật đã gặp trên server: `maybe_single().execute()` trả về None, đọc
    `.data` trên None gây AttributeError, bị `except Exception` bắt và đổi thành
    lỗi 500 "Failed to fetch 3D cake model".
    """
    client = MagicMock()
    client.table.side_effect = [
        MockQuery(returns_none=True),
        MockQuery(returns_none=True),
    ]

    with pytest.raises(Cake3DModelNotFoundError):
        Cake3DModelService(client).get_model("khong-ton-tai")


def test_get_model_ignores_empty_by_id_lookup_and_uses_slug():
    """UUID tra không ra dòng nào (None) thì vẫn phải thử tiếp bằng slug."""
    client = MagicMock()
    slug_query = MockQuery(data={"slug": "round-2-tier"})
    client.table.side_effect = [MockQuery(returns_none=True), slug_query]

    result = Cake3DModelService(client).get_model("round-2-tier")

    assert result["slug"] == "round-2-tier"
    assert ("eq", "slug", "round-2-tier") in slug_query.filters
