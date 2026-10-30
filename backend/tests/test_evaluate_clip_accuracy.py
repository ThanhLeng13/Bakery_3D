"""Regression tests for the independent 3D-filter measurement.

The script measures two different claims for each GLB render:
- unfiltered ranking: does top-1 identify the body shape?
- filtered contract: does "3D only" return only viewable products?

A failure/empty result in the first claim must not silently erase the image
from the denominator of the second claim.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "evaluate_clip_accuracy.py"


def _load_script_module():
    """Load the executable script without requiring scripts to be a package."""
    spec = importlib.util.spec_from_file_location("evaluate_clip_accuracy_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("unfiltered_outcome", ["raises", "empty"])
def test_filtered_measurement_survives_unfiltered_failure_or_empty_result(
    tmp_path, monkeypatch, unfiltered_outcome
):
    """Every readable query image remains in the 3D-only denominator.

    This protects against moving the filtered call below either `continue` in
    the unfiltered ranking branch. Such a move makes a flaky ordinary search
    make the 3D-only contract appear stronger than it really is.
    """
    module = _load_script_module()
    image = tmp_path / "mo_hinh_3d" / "round-1-tier__front.jpg"
    image.parent.mkdir()
    image.write_bytes(b"not-decoded: service is mocked")

    calls: list[bool | None] = []

    class FakeService:
        def search_by_image(self, _bytes, **kwargs):
            filtered = kwargs.get("has_3d_model")
            calls.append(filtered)
            if filtered is True:
                return {
                    "results": [
                        {
                            "name": "Mẫu mở được viewer",
                            "similarity": 0.8,
                            "three_d_model": {"slug": "round-1-tier"},
                        }
                    ]
                }
            if unfiltered_outcome == "raises":
                raise RuntimeError("ordinary ranking unavailable")
            return {"results": []}

    monkeypatch.setattr(module, "TEST_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "load_manifest",
        lambda: [
            {
                "group": "mo_hinh_3d",
                "label": "round-1-tier",
                "file": "mo_hinh_3d/round-1-tier__front.jpg",
            }
        ],
    )
    monkeypatch.setattr(module, "ClipSearchService", FakeService)

    assert module.main() == 0

    report = __import__("json").loads((tmp_path / "accuracy_report.json").read_text())
    # Unfiltered failure/rỗng has its own denominator: no body-ranking sample.
    assert report["n_3d_body"] == 0
    # But the same readable image was still measured once in 3D-only mode.
    assert report["filtered_3d_attempts"] == 1
    assert report["filtered_3d_all_viewable_rate"] == 100.0
    assert calls == [True, None]


@pytest.mark.parametrize("rank", [1, 3, 4, 5, 6])
def test_catalog_top_k_boundaries(tmp_path, monkeypatch, rank):
    """Top-5 must include rank five, not rank six or only top three."""
    import json

    module = _load_script_module()
    (tmp_path / "query.jpg").write_bytes(b"mock image")
    names = [f"Other {i}" for i in range(6)]
    names[rank - 1] = "Expected cake"

    class FakeService:
        def search_by_image(self, _bytes, **kwargs):
            return {"results": [
                {"name": name, "similarity": 0.8} for name in names
            ]}

    monkeypatch.setattr(module, "TEST_DIR", tmp_path)
    monkeypatch.setattr(module, "ClipSearchService", FakeService)
    monkeypatch.setattr(module, "load_manifest", lambda: [{
        "group": "trong_kho", "label": "Expected cake", "file": "query.jpg",
    }])
    assert module.main() == 0
    report = json.loads((tmp_path / "accuracy_report.json").read_text(encoding="utf-8"))
    assert report["n_in_catalog"] == 1
    for k in (1, 3, 5):
        assert report[f"top{k}_accuracy"] == (100.0 if rank <= k else 0.0)
        assert report["details"][0][f"correct_top{k}"] is (rank <= k)
    assert report["details"][0]["top5"] == names[:5]
