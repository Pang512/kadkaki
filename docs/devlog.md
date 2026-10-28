# KadKaki devlog

History before KadKaki is in the v3 devlog:
https://github.com/Pang512/malaysia-credit-card-rag/blob/main/docs/devlog.md

## 2026-10-28 · Phase 0: Fork from v3.2

**What was done**
- Froze v3 as release v3.2.0 and seeded KadKaki from that tag with git archive (tracked files only, so no keys, venv or bank PDFs)
- New public code repo, new private data repo, new Gemini key in its own Google Cloud project
- Read-only, single-repo GitHub token for the app to fetch its data
- Renamed the app and rewrote the README
- Deployed at https://kadkaki.streamlit.app/

**Findings**
- Free-tier limits (28 Oct 2026): Gemini 3.5 Flash-Lite 15 RPM / 500 RPD; Gemini 3.6 Flash 5 RPM / 20 RPD
- v3's fallback model (gemini-3.5-flash) was not available on the new project, so KadKaki's fallback is now gemini-3.6-flash
- The data repo is set by environment variables, so switching data repos needed no code change

**Parity check**
- Multi-turn regression suite: 48/48 checks (v3.2: 47/48)
- Live smoke test, 3 questions: all passed