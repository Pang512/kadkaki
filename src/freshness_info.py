"""When was each source last checked? Used by the app to show a date under every cited source.

The weekly freshness workflow writes the dates to freshness/freshness_state.json in the private
data repo. The app reads that file with the same read-only token it uses for its data
(DATA_REPO / DATA_REPO_TOKEN). Locally, without those settings, it falls back to
data/freshness_state.json if present. Nothing here ever raises: no date is better than a crash.
"""
import json
import os
from datetime import date
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
REMOTE_PATH = "freshness/freshness_state.json"
LOCAL_STATE = ROOT / "data" / "freshness_state.json"
SOURCES = ROOT / "data" / "sources.yaml"


def load_last_checked():
    """Return {doc_id: "YYYY-MM-DD"} for every document with a confirmed check."""
    state = _remote_state() or _local_state() or {}
    return {doc_id: entry["last_confirmed"]
            for doc_id, entry in state.get("documents", {}).items()
            if entry.get("last_confirmed")}


def _remote_state():
    repo, token = os.getenv("DATA_REPO"), os.getenv("DATA_REPO_TOKEN")
    if not repo or not token:
        return None
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/contents/{REMOTE_PATH}", timeout=10,
                         headers={"Authorization": f"Bearer {token}",
                                  "Accept": "application/vnd.github.raw+json"})
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _local_state():
    try:
        return json.loads(LOCAL_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_bank_docs():
    """Return {bank: [doc_id, ...]} for English documents, to place catalog sources."""
    try:
        docs = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["documents"]
    except Exception:
        return {}
    banks = {}
    for d in docs:
        if d.get("language", "en") == "en":
            banks.setdefault(d.get("bank"), []).append(d.get("doc_id"))
    return banks


def doc_id_for(source, chunks=(), known_ids=(), bank_docs=None):
    """Work out which registered document a cited source came from. Returns None if unsure."""
    if source.get("doc_id"):
        return source["doc_id"]
    chunk_id = source.get("chunk_id")
    if chunk_id:
        chunk = next((c for c in chunks if c.get("chunk_id") == chunk_id), None)
        if chunk and chunk.get("doc_id"):
            return chunk["doc_id"]
        # chunk ids usually start with the document id, e.g. "bankislam_credit_card_i_p4_c2"
        matches = [d for d in known_ids if str(chunk_id).startswith(d)]
        if matches:
            return max(matches, key=len)
    if bank_docs and source.get("bank"):
        ids = bank_docs.get(source["bank"], [])
        if len(ids) == 1:  # only when the bank has exactly one document; otherwise don't guess
            return ids[0]
    return None


def nice_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def checked_caption(source, chunks, dates, bank_docs=None):
    """The line shown under a source, or None when the document can't be identified."""
    known = set(dates) | {d for ids in (bank_docs or {}).values() for d in ids}
    doc_id = doc_id_for(source, chunks, known, bank_docs)
    if not doc_id:
        return None
    if doc_id in dates:
        return f"Checked against the bank's live document on {nice_date(dates[doc_id])}"
    return "Not yet checked against the bank's live document"
