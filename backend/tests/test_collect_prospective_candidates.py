"""Collector must try later results after a failed download or invalid image."""
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "collect_prospective_candidates.py"


@pytest.mark.parametrize("failure", ["download", "invalid_image"])
def test_bad_candidate_does_not_skip_later_results(tmp_path, monkeypatch, failure):
    # Stub only the network helper import; avoid its import-time stdout wrapper.
    helpers = ModuleType("collect_test_images")
    helpers.OUT_DIR = tmp_path
    helpers._fetch = lambda *_args, **_kwargs: None
    helpers.search_commons = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "collect_test_images", helpers)
    spec = importlib.util.spec_from_file_location("candidate_collector_test", SCRIPT)
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    (tmp_path / "manifest.json").write_text("[]", encoding="utf-8")
    collector.QUERIES = [("trong_kho", "cake", "query"), ("trong_kho", "cake", "query2")]
    candidates = [{"page": f"https://example.test/{i}", "url": str(i),
                   "license": "CC0", "artist": "author", "title": str(i)}
                  for i in range(2)]
    collector.search_commons = lambda *_args, **_kwargs: candidates
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    good = buffer.getvalue()
    calls = []

    def fetch(url, **_kwargs):
        calls.append(url)
        if url == "0":
            if failure == "download":
                raise OSError("connection lost")
            return b"not an image"
        return good

    collector._fetch = fetch
    monkeypatch.setattr(collector.time, "sleep", lambda _: None)
    collector.main()
    saved = json.loads((tmp_path / "prospective_candidates/manifest_candidates.json").read_text())
    assert saved[0]["source"] == "https://example.test/1"
    assert calls[:2] == ["0", "1"]
    assert len(saved) == 1
    # Second query has a bad candidate, followed by already-seen good bytes/source.
    # No invalid file may remain when none of that query's candidates is usable.
    assert not (tmp_path / "prospective_candidates/candidate_01.jpg").exists()
    assert (tmp_path / "prospective_candidates/candidate_00.jpg").read_bytes() == good


def test_query_search_failure_still_continues_next_query(tmp_path, monkeypatch):
    helpers = ModuleType("collect_test_images")
    helpers.OUT_DIR = tmp_path
    helpers._fetch = lambda *_args, **_kwargs: None
    helpers.search_commons = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "collect_test_images", helpers)
    spec = importlib.util.spec_from_file_location("candidate_collector_query_test", SCRIPT)
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    (tmp_path / "manifest.json").write_text("[]", encoding="utf-8")
    collector.QUERIES = [("trong_kho", "cake", "first"), ("trong_kho", "cake", "second")]
    calls = []

    def search(term, **_kwargs):
        calls.append(term)
        if term == "first":
            raise OSError("search unavailable")
        return []

    collector.search_commons = search
    monkeypatch.setattr(collector.time, "sleep", lambda _: None)
    collector.main()
    assert calls == ["first", "second"]
