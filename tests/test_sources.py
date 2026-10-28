"""Tests for src/sources.py. Run with: python -m pytest tests -q"""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sources import SOURCES, load_sources  # noqa: E402

GOOD_DOC = {
    "doc_id": "test_bank_cards",
    "bank": "Test Bank",
    "product": "Test Bank Credit Cards",
    "card_type": "conventional",
    "scope": "multi_card",
    "language": "en",
    "valid_as_at": "2026-10",
    "url": "https://example.com/pds.pdf",
    "tier": 1,
    "doc_type": "pds",
    "expected_version": None,
    "last_checked": None,
}


def write_registry(tmp_path, documents, blocked=None):
    path = tmp_path / "sources.yaml"
    data = {"version": 2, "documents": documents, "blocked_urls": blocked or []}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def doc(**changes):
    d = dict(GOOD_DOC)
    d.update(changes)
    return d


def test_real_registry_is_valid():
    registry = load_sources(SOURCES)
    assert len(registry.documents) >= 1


def test_real_registry_keeps_the_hlb_trap_blocked():
    registry = load_sources(SOURCES)
    blocked = {b.url for b in registry.blocked_urls}
    assert any("ImCard/hlb-product-disclosure-sheet-en.pdf" in url for url in blocked)


def test_good_document_passes(tmp_path):
    assert load_sources(write_registry(tmp_path, [doc()])).documents[0].doc_id == "test_bank_cards"


def test_duplicate_doc_id_fails(tmp_path):
    with pytest.raises(ValueError, match="duplicate doc_id"):
        load_sources(write_registry(tmp_path, [doc(), doc()]))


def test_blocked_url_fails(tmp_path):
    blocked = [{"url": GOOD_DOC["url"], "reason": "old", "noted": "2026-10-28"}]
    with pytest.raises(ValueError, match="blocked url"):
        load_sources(write_registry(tmp_path, [doc()], blocked))


def test_islamic_without_concept_fails(tmp_path):
    with pytest.raises(ValueError, match="shariah_concept"):
        load_sources(write_registry(tmp_path, [doc(card_type="islamic")]))


def test_tier_1_must_be_pds(tmp_path):
    with pytest.raises(ValueError, match="tier 1 is for PDS only"):
        load_sources(write_registry(tmp_path, [doc(doc_type="rewards_tnc")]))


def test_tier_2_rewards_tnc_passes(tmp_path):
    load_sources(write_registry(tmp_path, [doc(tier=2, doc_type="rewards_tnc")]))


def test_manual_download_needs_source_page(tmp_path):
    with pytest.raises(ValueError, match="source_page"):
        load_sources(write_registry(tmp_path, [doc(url="")]))


def test_bad_valid_as_at_fails(tmp_path):
    with pytest.raises(ValueError, match="YYYY"):
        load_sources(write_registry(tmp_path, [doc(valid_as_at="Oct 2026")]))


def test_misspelt_field_fails(tmp_path):
    bad = doc()
    bad["last_check"] = "2026-10-28"  # typo for last_checked
    with pytest.raises(ValueError, match="last_check"):
        load_sources(write_registry(tmp_path, [bad]))


def test_http_link_fails(tmp_path):
    with pytest.raises(ValueError, match="https"):
        load_sources(write_registry(tmp_path, [doc(url="http://example.com/pds.pdf")]))
