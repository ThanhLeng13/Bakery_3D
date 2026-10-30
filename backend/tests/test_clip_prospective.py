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
