"""Pre-inference checks must reject leakage and unverified query labels."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_clip_prospective.py"
spec = importlib.util.spec_from_file_location("clip_prospective_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def inputs(tmp_path):
    (tmp_path / "old.jpg").write_bytes(b"old")
    (tmp_path / "new.jpg").write_bytes(b"new")
    old = [{"file": "old.jpg", "source": "https://commons.test/File%3AOld"}]
    new = [{"file": "new.jpg", "source": "https://commons.test/File%3ANew",
            "group": "trong_kho", "label": "cake", "license": "CC0",
            "label_verified": True, "verified_by": "test reviewer"}]
    protocol = {"groups": ["trong_kho"], "minimum_per_group": 1}
    return old, new, protocol


def test_verified_new_query_passes(tmp_path):
    old, new, protocol = inputs(tmp_path)
    assert module.validate(new, old, tmp_path, protocol)["counts"] == {"trong_kho": 1}


@pytest.mark.parametrize("problem", ["source", "bytes", "unverified", "count", "path"])
def test_reject_invalid_prospective_data(tmp_path, problem):
    old, new, protocol = inputs(tmp_path)
    if problem == "source":
        new[0]["source"] = "https://commons.test/File:Old"
    elif problem == "bytes":
        (tmp_path / "new.jpg").write_bytes(b"old")
    elif problem == "unverified":
        new[0]["label_verified"] = False
    elif problem == "count":
        protocol["minimum_per_group"] = 2
    else:
        new[0]["file"] = "../outside.jpg"
    with pytest.raises(ValueError):
        module.validate(new, old, tmp_path, protocol)


@pytest.mark.parametrize("outcome", ["error", "empty", "below", "at_threshold"])
def test_prospective_measurement_keeps_failure_denominators(tmp_path, monkeypatch, outcome):
    import sys

    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    import evaluate_clip_prospective as evaluator

    old, new, protocol = inputs(tmp_path)
    (tmp_path / "negative.jpg").write_bytes(b"negative")
    new.append({**new[0], "file": "negative.jpg", "group": "ngoai_mien_banh",
                "source": "https://commons.test/File:Negative", "label": "not cake"})
    protocol.update(groups=["trong_kho", "ngoai_mien_banh"], threshold=0.5534,
                    protocol="test", model="test", embedding_dim=512)

    class FakeService:
        def search_by_image(self, raw, **kwargs):
            assert kwargs == {"match_count": 1, "match_threshold": 0.0}
            if outcome == "error":
                raise RuntimeError("service unavailable")
            if outcome == "empty":
                return {"results": []}
            score = 0.5534 if outcome == "at_threshold" else 0.1
            return {"results": [{"similarity": score}]}

    result = evaluator.evaluate(new, old, tmp_path, protocol, FakeService())
    assert result["threshold"] == 0.5534
    assert all(g["attempts"] == 1 for g in result["groups"].values())
    if outcome == "error":
        assert all(g["failures"] == 1 for g in result["groups"].values())
        assert result["in_catalog_acceptance_rate"] == 0
        assert result["out_of_domain_rejection_rate"] == 0
    elif outcome == "at_threshold":
        assert result["in_catalog_acceptance_rate"] == 1
        assert result["out_of_domain_rejection_rate"] == 0
    else:
        assert result["in_catalog_acceptance_rate"] == 0
        assert result["out_of_domain_rejection_rate"] == 1
