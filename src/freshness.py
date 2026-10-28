"""Freshness check for every document in data/sources.yaml.

    python src/freshness.py                  check every source, write a report
    python src/freshness.py --accept ID ...  mark reviewed changes as the new baseline
    python src/freshness.py --accept-all     accept everything currently seen

What it checks, per document:
  1. The link still returns a PDF (bank sites sometimes return an error page instead).
  2. The SHA-256 fingerprint of the file's text against the last ACCEPTED one. Any change is flagged
     until a person reviews it and accepts it. Nothing is ever accepted automatically,
     except the very first fingerprint of a new source (its baseline).
  3. The version label printed inside the PDF against `expected_version` in sources.yaml.
     When no label is set yet, it lists date-like lines it found, so a person can pick one.
And per bank page given as `source_page`:
  4. PDF links that are new or have disappeared since the last accepted check,
     and whether the document's own link is still on the page.

The state (fingerprints, links) lives in data/freshness_state.json. The report is written
to reports/freshness_latest.md. Neither contains any text from the banks' documents.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import pymupdf as fitz  # PyMuPDF 1.24+
except ImportError:  # older PyMuPDF
    import fitz
import requests

from sources import ROOT, load_sources

STATE = ROOT / "data" / "freshness_state.json"
REPORT = ROOT / "reports" / "freshness_latest.md"
# Some bank websites reject requests that don't look like a browser (same as download.py)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

MONTHS = (r"JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?|"
          r"SEP(?:T|TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?|"
          r"JANUARI|FEBRUARI|MAC|MEI|JUN|JULAI|OGOS|OKTOBER|DISEMBER")
# A line is a candidate version label if it mentions a month and a year, or a numeric date
DATE_LIKE = re.compile(rf"\b(?:{MONTHS})\b[\s,.-]*\d{{4}}\b|\b\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{4}}\b", re.I)

ATTENTION = {"changed", "version_mismatch", "unreachable", "not_pdf", "manual", "local_only",
             "new_links", "missing_links", "not_linked", "page_unreachable"}
# Problems that need a person this week. "manual" is a standing reminder instead (monthly issue).
REVIEW = ATTENTION - {"manual", "local_only"}
# A document is "confirmed" on a date when its live file was fetched and matched the accepted version.
NOT_CONFIRMED = {"changed", "version_mismatch", "unreachable", "not_pdf", "manual", "local_only"}

NEXT_STEP = {
    "changed": "The file is different from the accepted version. Open it, check what changed, then accept it.",
    "version_mismatch": "The expected version label is not in the file. The bank may have published a new version, "
                        "or the link may now point to a different file.",
    "unreachable": "Open the link in a browser. If it works there, the site may block scripts: download it by hand.",
    "not_pdf": "The link returned a web page instead of a PDF. The file may have moved: find it on the bank's site.",
    "manual": "No direct link. Download it from the bank page and compare with your copy in data/raw.",
    "local_only": "This bank blocks GitHub's computers. Run the check from your laptop (see the data repo README).",
    "new_links": "New PDF links appeared on the page. Check for a new PDS or a new card.",
    "missing_links": "PDF links disappeared from the page. A document may have moved or been withdrawn.",
    "not_linked": "This document's link is no longer on its bank page. It may have been replaced.",
    "page_unreachable": "The bank page could not be loaded. Check it in a browser.",
}


# ---------- fetching and reading ----------

class Fetched:
    def __init__(self, content=None, error=None):
        self.content, self.error = content, error


def fetch(url):
    """Download a URL. Never raises: returns Fetched(content) or Fetched(error=...)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return Fetched(content=r.content)
    except requests.exceptions.HTTPError as e:
        return Fetched(error=f"HTTP {e.response.status_code}")
    except requests.exceptions.Timeout:
        return Fetched(error="timed out after 30 s")
    except requests.exceptions.ConnectionError:
        return Fetched(error="could not connect")
    except Exception as e:  # anything else: keep it short and readable
        return Fetched(error=type(e).__name__)


def pdf_text(content):
    """All text in the PDF, page by page."""
    with fitz.open(stream=content, filetype="pdf") as doc:
        return [page.get_text() for page in doc]


def normalise(text):
    return re.sub(r"\s+", " ", text).strip().upper()


def label_candidates(pages, limit=6):
    """Short date-like lines from the first and last page: likely version or 'valid as at' labels."""
    found = []
    for text in {0: pages[0], len(pages) - 1: pages[-1]}.values() if pages else []:
        for line in text.splitlines():
            line = " ".join(line.split())
            if 4 <= len(line) <= 80 and DATE_LIKE.search(line) and line not in found:
                found.append(line)
    return found[:limit]


class _PdfLinks(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.links = base, set()

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href")
        if tag == "a" and href:
            url = urljoin(self.base, href.strip())
            if urlparse(url).path.lower().endswith(".pdf"):
                self.links.add(url.split("#")[0])


def pdf_links(html_bytes, base):
    parser = _PdfLinks(base)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    return sorted(parser.links)


# ---------- the check ----------

def check_document(doc, entry, fetcher):
    """Check one document. Updates its state entry and returns its result."""
    result = {"doc_id": doc.doc_id, "bank": doc.bank, "flags": [], "candidates": [], "detail": ""}
    if not doc.url:
        result["flags"].append("manual")
        result["detail"] = doc.source_page or ""
        return result
    got = fetcher(doc.url)
    if got.error:
        result["flags"].append("unreachable")
        result["detail"] = got.error
        return result
    if not got.content.startswith(b"%PDF"):
        result["flags"].append("not_pdf")
        return result

    pages = pdf_text(got.content)
    # Two fingerprints: the file's bytes, and its text. A PDF can be re-saved (new internal IDs or
    # timestamps) with the same words, so only a TEXT change counts as "changed".
    file_sha = hashlib.sha256(got.content).hexdigest()
    text_sha = hashlib.sha256(normalise(" ".join(pages)).encode("utf-8")).hexdigest()
    entry["latest_sha256"], entry["latest_text_sha256"] = file_sha, text_sha
    if not entry.get("accepted_text_sha256"):
        entry["accepted_sha256"], entry["accepted_text_sha256"] = file_sha, text_sha
        result["flags"].append("baseline")
    elif text_sha != entry["accepted_text_sha256"]:
        result["flags"].append("changed")
    elif file_sha != entry.get("accepted_sha256"):
        result["flags"].append("resaved")
        entry["accepted_sha256"] = file_sha  # same words, new file: nothing to review

    result["candidates"] = label_candidates(pages)
    if doc.expected_version:
        found = normalise(doc.expected_version) in normalise(" ".join(pages))
        entry["version_found"] = found
        if not found:
            result["flags"].append("version_mismatch")
            result["detail"] = f"expected \"{doc.expected_version}\""
    else:
        result["flags"].append("no_expected_version")
    return result


def check_page(url, doc_urls, entry, fetcher):
    """Check one bank page for new or missing PDF links."""
    result = {"page": url, "flags": [], "new": [], "missing": [], "not_linked": []}
    got = fetcher(url)
    if got.error:
        result["flags"].append("page_unreachable")
        return result
    links = pdf_links(got.content, url)
    entry["latest_links"] = links
    if "accepted_links" not in entry:
        entry["accepted_links"] = links
        result["flags"].append("baseline")
    else:
        result["new"] = sorted(set(links) - set(entry["accepted_links"]))
        result["missing"] = sorted(set(entry["accepted_links"]) - set(links))
        if result["new"]:
            result["flags"].append("new_links")
        if result["missing"]:
            result["flags"].append("missing_links")
    result["not_linked"] = [u for u in doc_urls if u and u not in links]
    if result["not_linked"]:
        result["flags"].append("not_linked")
    return result


def run_check(registry, state, fetcher=fetch, today=None, delay=1.0, ci=False):
    """Check every document and bank page. Updates `state` in place and returns the results.

    ci=True (on GitHub) skips documents marked remote_check: false, whose sites block GitHub.
    """
    today = (today or date.today()).isoformat()
    docs_state = state.setdefault("documents", {})
    pages_state = state.setdefault("pages", {})
    doc_results, page_results = [], []

    for doc in registry.documents:
        entry = docs_state.setdefault(doc.doc_id, {})
        if ci and not doc.remote_check:
            doc_results.append({"doc_id": doc.doc_id, "bank": doc.bank, "flags": ["local_only"],
                                "candidates": [], "detail": ""})
            continue
        result = check_document(doc, entry, fetcher)
        doc_results.append(result)
        if doc.url:
            entry["last_fetched"] = today
        if not (NOT_CONFIRMED & set(result["flags"])):
            entry["last_confirmed"] = today
        time.sleep(delay)

    pages = {}
    for doc in registry.documents:
        if doc.source_page:
            pages.setdefault(doc.source_page, []).append(doc.url)
    for url, doc_urls in pages.items():
        entry = pages_state.setdefault(url, {})
        page_results.append(check_page(url, doc_urls, entry, fetcher))
        entry["last_fetched"] = today
        time.sleep(delay)

    return {"date": today, "documents": doc_results, "pages": page_results}


def accept(state, ids, accept_all=False, registry=None):
    """Make the latest seen fingerprints (and page links) the accepted baseline. Returns what was accepted."""
    accepted = []
    docs_state = state.get("documents", {})
    pages_state = state.get("pages", {})
    for doc_id, entry in docs_state.items():
        if (accept_all or doc_id in ids) and entry.get("latest_text_sha256"):
            entry["accepted_sha256"] = entry["latest_sha256"]
            entry["accepted_text_sha256"] = entry["latest_text_sha256"]
            if entry.get("last_fetched"):
                entry["last_confirmed"] = entry["last_fetched"]  # a person has now reviewed that file
            accepted.append(doc_id)
    page_urls = set(pages_state) if accept_all else set()
    if registry and not accept_all:
        page_urls = {d.source_page for d in registry.documents if d.doc_id in ids and d.source_page}
    for url in page_urls:
        entry = pages_state.get(url, {})
        if "latest_links" in entry:
            entry["accepted_links"] = entry["latest_links"]
            accepted.append(url)
    return accepted


# ---------- report ----------

def needs_attention(results):
    return [r for r in results["documents"] + results["pages"] if ATTENTION & set(r["flags"])]


def issue_for(results, today=None):
    """Return (title, body) for a GitHub issue, or None when nobody needs to act.

    An issue is opened when something needs review this week, and once a month (first 7 days)
    as a reminder for documents that can only be checked by hand.
    """
    day = (today or date.fromisoformat(results["date"])).day
    review = [r for r in results["documents"] + results["pages"] if REVIEW & set(r["flags"])]
    manual = [r for r in results["documents"] if {"manual", "local_only"} & set(r["flags"])]
    if review:
        title = f"Freshness check {results['date']}: {len(review)} item(s) to review"
    elif manual and day <= 7:
        title = f"Monthly reminder {results['date']}: {len(manual)} document(s) to check by hand"
    else:
        return None
    body = render_report(results) + (
        "\n**When done:** for each reviewed change, open Actions → Freshness check → Run workflow, "
        "type the doc_id(s) in *accept* (separated by spaces), then close this issue.\n")
    return title, body


def render_report(results):
    lines = [f"# KadKaki freshness report: {results['date']}", ""]
    attention = needs_attention(results)
    if attention:
        lines += [f"**Status: ATTENTION NEEDED** ({len(attention)} item(s))", ""]
    else:
        lines += ["**Status: ALL CLEAR**", ""]

    review = [r for r in results["documents"] if {"changed", "version_mismatch", "not_pdf", "unreachable"} & set(r["flags"])]
    if review:
        lines += ["## Needs review", "", "| Document | Bank | What happened | Next step |", "|---|---|---|---|"]
        for r in review:
            for flag in r["flags"]:
                if flag in NEXT_STEP and flag != "manual":
                    what = flag.replace("_", " ") + (f": {r['detail']}" if r["detail"] else "")
                    lines.append(f"| `{r['doc_id']}` | {r['bank']} | {what} | {NEXT_STEP[flag]} |")
        lines.append("")

    page_issues = [p for p in results["pages"] if ATTENTION & set(p["flags"])]
    if page_issues:
        lines += ["## Bank pages", ""]
        for p in page_issues:
            lines.append(f"**{p['page']}**")
            for flag in p["flags"]:
                if flag in NEXT_STEP:
                    lines.append(f"- {flag.replace('_', ' ')}: {NEXT_STEP[flag]}")
            for label, urls in (("New", p["new"]), ("Missing", p["missing"]), ("Not linked", p["not_linked"])):
                lines += [f"  - {label}: {u}" for u in urls]
            lines.append("")

    local = [r for r in results["documents"] if "local_only" in r["flags"]]
    if local:
        lines += ["## Check from your laptop", "", NEXT_STEP["local_only"], ""]
        lines += [f"- `{r['doc_id']}` ({r['bank']})" for r in local]
        lines.append("")

    manual = [r for r in results["documents"] if "manual" in r["flags"]]
    if manual:
        lines += ["## Manual check needed", ""]
        lines += [f"- `{r['doc_id']}` ({r['bank']}): {NEXT_STEP['manual']} {r['detail']}" for r in manual]
        lines.append("")

    unset = [r for r in results["documents"] if "no_expected_version" in r["flags"]]
    if unset:
        lines += ["## Version labels not set yet", "",
                  "Pick the line that is the document's version or 'valid as at' label and put it in "
                  "`expected_version` in sources.yaml, exactly as printed.", ""]
        for r in unset:
            found = "; ".join(f"`{c}`" for c in r["candidates"]) or "no date-like lines found"
            lines.append(f"- `{r['doc_id']}`: {found}")
        lines.append("")

    baseline = [r.get("doc_id") or r.get("page") for r in results["documents"] + results["pages"] if "baseline" in r["flags"]]
    if baseline:
        lines += ["## New baselines recorded", "", "First check of these sources; their fingerprints are now the reference.", ""]
        lines += [f"- {b}" for b in baseline]
        lines.append("")

    ok = [r["doc_id"] for r in results["documents"] if not (ATTENTION & set(r["flags"]))]
    lines += ["## Unchanged and reachable", "", ", ".join(f"`{d}`" for d in ok) or "none", "",
              "---", "After reviewing a change: `python src/freshness.py --accept <doc_id>`"]
    return "\n".join(lines) + "\n"


# ---------- command line ----------

def load_state(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_state(state, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check KadKaki's sources for changes.")
    parser.add_argument("--accept", nargs="+", metavar="DOC_ID", help="accept the latest version of these documents")
    parser.add_argument("--accept-all", action="store_true", help="accept everything currently seen")
    parser.add_argument("--state", default=STATE, help="state file (default: data/freshness_state.json)")
    parser.add_argument("--report", default=REPORT, help="report file (default: reports/freshness_latest.md)")
    parser.add_argument("--ci", action="store_true", help="running on GitHub: skip sources marked remote_check: false")
    parser.add_argument("--issue", help="if someone needs to act, write an issue (title on line 1) to this file")
    args = parser.parse_args(argv)

    registry = load_sources()
    state = load_state(args.state)

    if args.accept or args.accept_all:
        accepted = accept(state, set(args.accept or []), args.accept_all, registry)
        save_state(state, args.state)
        print("Accepted:", ", ".join(accepted) if accepted else "nothing (run a check first?)")
        return 0

    print(f"Checking {len(registry.documents)} documents...")
    results = run_check(registry, state, ci=args.ci)
    save_state(state, args.state)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_report(results), encoding="utf-8")

    if args.issue:
        issue_path, issue = Path(args.issue), issue_for(results)
        if issue:
            issue_path.parent.mkdir(parents=True, exist_ok=True)
            issue_path.write_text(issue[0] + "\n" + issue[1], encoding="utf-8")
            print("Issue to open:", issue[0])
        elif issue_path.exists():
            issue_path.unlink()

    attention = needs_attention(results)
    print(f"{'ATTENTION NEEDED' if attention else 'ALL CLEAR'}: {len(attention)} item(s). Report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
