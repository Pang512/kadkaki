"""Load and validate data/sources.yaml, KadKaki's registry of official documents.

Run it after every edit to sources.yaml:
    python src/sources.py

It prints one line per document and stops with a clear message if anything is wrong.
Other scripts (the freshness checker in KK-05) import load_sources() from here.
"""
import re
import sys
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.yaml"

DOC_ID = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
# "unknown", or a date at year, month or day precision
VALID_AS_AT = re.compile(r"^(unknown|\d{4}(-\d{2}(-\d{2})?)?)$")


class Document(BaseModel):
    """One official document KadKaki reads facts from."""

    model_config = ConfigDict(extra="forbid")  # a misspelt field name is an error, not silently ignored

    doc_id: str
    bank: str
    product: str
    card_type: Literal["conventional", "islamic"]
    shariah_concept: Optional[str] = None
    scope: Literal["single_card", "multi_card"]
    language: Literal["en", "ms"]
    valid_as_at: str = "unknown"
    url: str = ""
    source_page: Optional[str] = None
    tier: Literal[1, 2]
    doc_type: Literal["pds", "product_page", "rewards_tnc"]
    expected_version: Optional[str] = None
    last_checked: Optional[date] = None
    notes: Optional[str] = None
    # False when the bank's site blocks GitHub's computers: the weekly run then skips it
    # and a monthly reminder asks for a check from a laptop in Malaysia instead.
    remote_check: bool = True

    @field_validator("doc_id")
    @classmethod
    def doc_id_format(cls, value):
        if not DOC_ID.match(value):
            raise ValueError("use lowercase letters, numbers and single underscores, e.g. hlb_credit_cards_en")
        return value

    @field_validator("valid_as_at", mode="before")
    @classmethod
    def valid_as_at_format(cls, value):
        value = str(value)  # YAML may read 2026-10-01 as a date
        if not VALID_AS_AT.match(value):
            raise ValueError('use "unknown", YYYY, YYYY-MM or YYYY-MM-DD')
        return value

    @field_validator("url", "source_page")
    @classmethod
    def https_only(cls, value):
        if value and not value.startswith("https://"):
            raise ValueError("links must start with https://")
        return value

    @model_validator(mode="after")
    def consistent(self):
        if self.card_type == "islamic" and not self.shariah_concept:
            raise ValueError("Islamic cards need a shariah_concept (e.g. Tawarruq)")
        if not self.url and not self.source_page:
            raise ValueError("give a url, or a source_page for manual download")
        if self.tier == 1 and self.doc_type != "pds":
            raise ValueError("tier 1 is for PDS only; product pages and T&Cs are tier 2")
        if self.tier == 2 and self.doc_type == "pds":
            raise ValueError("a PDS is tier 1")
        if self.last_checked and self.last_checked > date.today():
            raise ValueError("last_checked can't be in the future")
        return self


class BlockedUrl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    reason: str
    noted: date


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[2]
    documents: list[Document]
    blocked_urls: list[BlockedUrl] = []

    @model_validator(mode="after")
    def registry_rules(self):
        ids = [d.doc_id for d in self.documents]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate doc_id: {', '.join(duplicates)}")
        blocked = {b.url for b in self.blocked_urls}
        used = [d.doc_id for d in self.documents if d.url in blocked]
        if used:
            raise ValueError(f"these documents use a blocked url: {', '.join(used)}")
        return self


def load_sources(path=SOURCES) -> Registry:
    """Read sources.yaml and return the validated registry. Raises ValueError if anything is wrong."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        return Registry.model_validate(raw)
    except ValidationError as e:
        lines = []
        for err in e.errors():
            where = _describe(raw, err["loc"])
            lines.append(f"  - {where}: {err['msg']}")
        raise ValueError("sources.yaml has problems:\n" + "\n".join(lines)) from None


def _describe(raw, loc):
    """Turn a pydantic error location like ('documents', 3, 'tier') into 'hlb_credit_cards_en → tier'."""
    if len(loc) >= 2 and loc[0] == "documents" and isinstance(loc[1], int):
        try:
            name = raw["documents"][loc[1]].get("doc_id", f"document #{loc[1] + 1}")
        except (IndexError, AttributeError, KeyError, TypeError):
            name = f"document #{loc[1] + 1}"
        rest = " → ".join(str(part) for part in loc[2:])
        return f"{name} → {rest}" if rest else name
    return " → ".join(str(part) for part in loc) or "file"


def main():
    try:
        registry = load_sources()
    except ValueError as e:
        print(e)
        sys.exit(1)
    for d in registry.documents:
        checked = d.last_checked.isoformat() if d.last_checked else "never"
        version = d.expected_version or "-"
        print(f"tier {d.tier}  {d.doc_id:<28} valid {d.valid_as_at:<11} checked {checked:<10} version {version}")
    print(f"\nOK: {len(registry.documents)} documents, {len(registry.blocked_urls)} blocked url(s).")


if __name__ == "__main__":
    main()
