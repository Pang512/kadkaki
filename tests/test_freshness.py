"""Tests for src/freshness.py. No internet needed: downloads are faked.
Run with: python -m pytest tests -q"""
import sys
from datetime import date
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from freshness import Fetched, accept, issue_for, label_candidates, pdf_links, render_report, run_check  # noqa: E402
from sources import load_sources  # noqa: E402

TODAY = date(2026, 10, 28)
PDS_URL = "https://bank.example/pds.pdf"
PAGE_URL = "https://bank.example/cards"


def make_pdf(*lines):
    """A tiny one-page PDF containing the given lines of text."""
    doc = fitz.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((72, 72 + 20 * i), line)
    data = doc.tobytes()
    doc.close()
    return data


def make_page(*pdf_hrefs):
    links = "".join(f'<a href="{h}">doc</a>' for h in pdf_hrefs)
    return f"<html><body>{links}<a href='/about'>About</a></body></html>".encode()


def registry(tmp_path, **changes):
    doc = {"doc_id": "test_bank_cards", "bank": "Test Bank", "product": "Test cards",
           "card_type": "conventional", "scope": "multi_card", "language": "en",
           "valid_as_at": "2026-10", "url": PDS_URL, "tier": 1, "doc_type": "pds",
           "expected_version": None, "last_checked": None}
    doc.update(changes)
    path = tmp_path / "sources.yaml"
    path.write_text(yaml.safe_dump({"version": 2, "documents": [doc], "blocked_urls": []}), encoding="utf-8")
    return load_sources(path)


def fake(responses):
    """A fetcher that serves canned bytes, or an error for anything not listed."""
    def fetcher(url):
        if url in responses:
            return Fetched(content=responses[url])
        return Fetched(error="404 Not Found")
    return fetcher


def run(reg, state, responses):
    return run_check(reg, state, fake(responses), today=TODAY, delay=0)


def flags(results):
    return results["documents"][0]["flags"]


# ---------- fingerprints ----------

def test_first_check_records_a_baseline(tmp_path):
    state = {}
    results = run(registry(tmp_path), state, {PDS_URL: make_pdf("Version A")})
    assert "baseline" in flags(results)
    assert state["documents"]["test_bank_cards"]["accepted_sha256"]


def test_unchanged_file_is_ok(tmp_path):
    reg, state, pdf = registry(tmp_path), {}, make_pdf("Version A")
    run(reg, state, {PDS_URL: pdf})
    results = run(reg, state, {PDS_URL: pdf})
    assert "changed" not in flags(results) and "baseline" not in flags(results)


def test_changed_file_is_flagged_until_accepted(tmp_path):
    reg, state, new = registry(tmp_path), {}, make_pdf("Version B")
    run(reg, state, {PDS_URL: make_pdf("Version A")})
    assert "changed" in flags(run(reg, state, {PDS_URL: new}))
    # still flagged next week if nobody reviewed it
    assert "changed" in flags(run(reg, state, {PDS_URL: new}))
    accept(state, {"test_bank_cards"})
    assert "changed" not in flags(run(reg, state, {PDS_URL: new}))


def test_resaved_file_with_same_words_is_not_a_change(tmp_path):
    """Each save gives a PDF new internal IDs, so the bytes differ even when the words don't."""
    reg, state = registry(tmp_path), {}
    first, second = make_pdf("Version A"), make_pdf("Version A")
    assert first != second
    run(reg, state, {PDS_URL: first})
    result = flags(run(reg, state, {PDS_URL: second}))
    assert "resaved" in result and "changed" not in result


# ---------- version labels: the Hong Leong trap ----------

def test_old_hlb_style_file_fails_the_version_check(tmp_path):
    """The real trap: a search result serves the 2019 PDS while we expect the October 2026 one."""
    reg = registry(tmp_path, expected_version="CC PDS ENG V OCT 2026")
    results = run(reg, {}, {PDS_URL: make_pdf("PRODUCT DISCLOSURE SHEET", "V001 APR 2019")})
    assert "version_mismatch" in flags(results)
    assert any("APR 2019" in c for c in results["documents"][0]["candidates"])


def test_expected_label_is_found_despite_spacing_and_case(tmp_path):
    reg = registry(tmp_path, expected_version="CC PDS ENG V OCT 2026")
    results = run(reg, {}, {PDS_URL: make_pdf("cc pds eng   v oct 2026")})
    assert "version_mismatch" not in flags(results)


def test_label_candidates_pick_date_like_lines():
    pages = ["PRODUCT DISCLOSURE SHEET\nCC PDS ENG V OCT 2026\nAnnual fee RM98", "Valid as at 01/10/2026"]
    found = label_candidates(pages)
    assert "CC PDS ENG V OCT 2026" in found
    assert "Valid as at 01/10/2026" in found
    assert "Annual fee RM98" not in found


def test_missing_expected_version_lists_candidates(tmp_path):
    results = run(registry(tmp_path), {}, {PDS_URL: make_pdf("Effective 31 December 2025")})
    assert "no_expected_version" in flags(results)
    assert results["documents"][0]["candidates"] == ["Effective 31 December 2025"]


# ---------- unreachable, wrong content, manual ----------

def test_unreachable_link_is_flagged(tmp_path):
    assert "unreachable" in flags(run(registry(tmp_path), {}, {}))


def test_web_page_instead_of_pdf_is_flagged(tmp_path):
    assert "not_pdf" in flags(run(registry(tmp_path), {}, {PDS_URL: b"<html>Error</html>"}))


def test_manual_document_is_flagged(tmp_path):
    reg = registry(tmp_path, url="", source_page=PAGE_URL)
    results = run(reg, {}, {PAGE_URL: make_page("/other.pdf")})
    assert "manual" in flags(results)


# ---------- bank pages ----------

def test_page_links_new_missing_and_not_linked(tmp_path):
    reg, state = registry(tmp_path, source_page=PAGE_URL), {}
    pdf = make_pdf("x")
    first = run(reg, state, {PDS_URL: pdf, PAGE_URL: make_page("/pds.pdf", "/tnc.pdf")})
    assert "baseline" in first["pages"][0]["flags"]
    later = run(reg, state, {PDS_URL: pdf, PAGE_URL: make_page("/tnc.pdf", "/pds-2027.pdf")})
    page = later["pages"][0]
    assert page["new"] == ["https://bank.example/pds-2027.pdf"]
    assert page["missing"] == ["https://bank.example/pds.pdf"]
    assert page["not_linked"] == [PDS_URL]


def test_pdf_links_resolves_relative_links_and_ignores_other_pages():
    links = pdf_links(make_page("files/a.PDF", "https://other.example/b.pdf?x=1"), PAGE_URL)
    assert links == ["https://bank.example/files/a.PDF", "https://other.example/b.pdf?x=1"]


# ---------- report ----------

def test_report_says_all_clear_or_attention(tmp_path):
    reg, state, pdf = registry(tmp_path, expected_version="V OCT 2026"), {}, make_pdf("V OCT 2026")
    assert "ALL CLEAR" in render_report(run(reg, state, {PDS_URL: pdf}))
    report = render_report(run(reg, state, {PDS_URL: make_pdf("V NOV 2026")}))
    assert "ATTENTION NEEDED" in report and "test_bank_cards" in report


# ---------- last confirmed (shown in the app) and issues (KK-06) ----------

def test_last_confirmed_set_only_when_file_matches(tmp_path):
    reg, state = registry(tmp_path), {}
    run(reg, state, {PDS_URL: make_pdf("Version A")})
    assert state["documents"]["test_bank_cards"]["last_confirmed"] == "2026-10-28"
    later = date(2026, 11, 4)
    run_check(reg, state, fake({PDS_URL: make_pdf("Version B")}), today=later, delay=0)
    assert state["documents"]["test_bank_cards"]["last_confirmed"] == "2026-10-28"  # changed: not confirmed
    accept(state, {"test_bank_cards"})
    assert state["documents"]["test_bank_cards"]["last_confirmed"] == "2026-11-04"  # reviewed by a person


def test_unreachable_keeps_old_confirmed_date(tmp_path):
    reg, state = registry(tmp_path), {}
    run(reg, state, {PDS_URL: make_pdf("Version A")})
    run_check(reg, state, fake({}), today=date(2026, 11, 4), delay=0)
    assert state["documents"]["test_bank_cards"]["last_confirmed"] == "2026-10-28"


def test_no_issue_when_all_clear(tmp_path):
    reg, state, pdf = registry(tmp_path), {}, make_pdf("Version A")
    run(reg, state, {PDS_URL: pdf})
    assert issue_for(run(reg, state, {PDS_URL: pdf})) is None


def test_issue_when_a_document_changed(tmp_path):
    reg, state = registry(tmp_path), {}
    run(reg, state, {PDS_URL: make_pdf("Version A")})
    title, body = issue_for(run(reg, state, {PDS_URL: make_pdf("Version B")}))
    assert "1 item(s) to review" in title and "test_bank_cards" in body and "accept" in body


def test_manual_documents_get_a_monthly_reminder_only(tmp_path):
    reg = registry(tmp_path, url="", source_page=PAGE_URL)
    page = {PAGE_URL: make_page("/x.pdf")}
    state = {}
    run(reg, state, page)  # baseline for the page
    early = run_check(reg, state, fake(page), today=date(2026, 11, 2), delay=0)
    mid = run_check(reg, state, fake(page), today=date(2026, 11, 16), delay=0)
    assert issue_for(early)[0].startswith("Monthly reminder")
    assert issue_for(mid) is None
