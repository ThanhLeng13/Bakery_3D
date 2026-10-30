"""Leakage and test-set isolation checks for retrospective threshold protocol."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "evaluate_clip_holdout.py"
spec = importlib.util.spec_from_file_location("clip_holdout_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def data(tmp_path):
    items, details, ood = [], [], []
    for group in module.GROUPS:
        for i in range(8):
            file = f"{group}_{i}.jpg"
            (tmp_path / file).write_bytes(f"{group}:{i}".encode())
            items.append({"group": group, "label": f"{group}:{i}", "file": file,
                          "source": f"https://example.test/{group}/{i}"})
            (details if group == "trong_kho" else ood).append({"file": file, "sim1": 0.2 + i / 20})
    return items, {"details": details, "details_out_of_domain": ood}


def test_no_source_label_or_bytes_cross_partitions(tmp_path):
    items, report = data(tmp_path)
    # A common source connects labels; identical bytes connect other sources.
    items[1]["source"] = items[0]["source"]
    (tmp_path / items[2]["file"]).write_bytes((tmp_path / items[0]["file"]).read_bytes())
    items[3]["label"] = items[0]["label"]
    rows = module.evaluate(items, report, tmp_path)["queries"]
    for key in ("source", "label", "sha256", "component"):
        a = {r[key] for r in rows if r["split"] == "calibration"}
        b = {r[key] for r in rows if r["split"] == "test"}
        assert not a & b


def test_test_scores_never_select_threshold(tmp_path):
    items, report = data(tmp_path)
    first = module.evaluate(items, report, tmp_path)
    test_files = {r["file"] for r in first["queries"] if r["split"] == "test"}
    for row in report["details"] + report["details_out_of_domain"]:
        if row["file"] in test_files:
            row["sim1"] = 0.999
    second = module.evaluate(list(reversed(items)), report, tmp_path)
    assert first["threshold"] == second["threshold"]
    assert first["calibration"] == second["calibration"]
    assert {r["file"]: r["split"] for r in first["queries"]} == {
        r["file"]: r["split"] for r in second["queries"]}


def test_missing_scores_fail_instead_of_improving_denominator(tmp_path):
    items, report = data(tmp_path)
    report["details"].pop()
    with pytest.raises(ValueError, match="Missing query score"):
        module.evaluate(items, report, tmp_path)


def test_missing_source_is_not_treated_as_independent(tmp_path):
    items, report = data(tmp_path)
    items[0]["source"] = "?"
    with pytest.raises(ValueError, match="Unverified source"):
        module.evaluate(items, report, tmp_path)
