"""Tests for src/freshness_info.py. Run with: python -m pytest tests -q"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import freshness_info  # noqa: E402
from freshness_info import checked_caption, doc_id_for, load_last_checked, nice_date  # noqa: E402

CHUNKS = [{"chunk_id": "c1", "doc_id": "cimb_credit_cards"},
          {"chunk_id": "bankislam_credit_card_i_p4_c2"}]
DATES = {"cimb_credit_cards": "2026-10-29", "bankislam_credit_card_i": "2026-10-05"}
BANKS = {"CIMB": ["cimb_credit_cards"], "Maybank": ["maybank_cashback_platinum", "maybank_islamic_nadi"]}


def test_doc_id_from_source_chunk_prefix_and_bank():
    assert doc_id_for({"doc_id": "ocbc_credit_cards"}) == "ocbc_credit_cards"
    assert doc_id_for({"chunk_id": "c1"}, CHUNKS) == "cimb_credit_cards"
    assert doc_id_for({"chunk_id": "bankislam_credit_card_i_p4_c2"}, CHUNKS, DATES) == "bankislam_credit_card_i"
    assert doc_id_for({"bank": "CIMB"}, bank_docs=BANKS) == "cimb_credit_cards"


def test_no_guess_when_bank_has_several_documents():
    assert doc_id_for({"bank": "Maybank"}, bank_docs=BANKS) is None


def test_caption_text():
    assert checked_caption({"chunk_id": "c1"}, CHUNKS, DATES) == \
        "Checked against the bank's live document on 29 Oct 2026"
    assert checked_caption({"bank": "CIMB"}, [], {}, BANKS) == "Not yet checked against the bank's live document"
    assert checked_caption({"bank": "Unknown"}, [], DATES, BANKS) is None


def test_nice_date():
    assert nice_date("2026-11-02") == "2 Nov 2026"


def test_local_fallback_and_missing_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_REPO", raising=False)
    monkeypatch.delenv("DATA_REPO_TOKEN", raising=False)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"documents": {"a": {"last_confirmed": "2026-10-29"}, "b": {}}}))
    monkeypatch.setattr(freshness_info, "LOCAL_STATE", state)
    assert load_last_checked() == {"a": "2026-10-29"}
    monkeypatch.setattr(freshness_info, "LOCAL_STATE", tmp_path / "missing.json")
    assert load_last_checked() == {}
