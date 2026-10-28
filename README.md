# KadKaki

A neutral, non-commercial assistant that helps young Malaysians choose and understand
credit cards, conventional and Islamic, using the banks' own official documents.
Every fact is dated and linked, and KadKaki says "I don't know" instead of guessing.

> **Status: Phase 0.** Currently runs the same engine as v3.2 (8 banks).
> Expanding to the whole Malaysian market.

## Principles
- **Official sources only:** facts come from banks' Product Disclosure Sheets and product pages, never from comparison sites
- **Neutral:** no affiliate links, no bank partnerships
- **Responsible:** shows costs and debt risk, not just rewards
- **Inclusive:** explains Islamic credit card (Credit Card-i) concepts in plain language

## Roadmap
| Phase | Focus |
|---|---|
| 0 | Fork from v3.2 |
| 1 | Weekly freshness checks on every source |
| 2 | Coverage of all major card issuers |
| 3 | Card Finder: personal shortlist in under a minute |
| 4 | Rewards, cashback and perks |
| 5 | My Wallet and short lessons |
| 6 | Market test with fresh graduates |

## Run locally
```
python -m venv .kkvenv
.kkvenv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your-key
DATA_REPO=owner/data-repo
DATA_REPO_TOKEN=read-only-token
```

Then:
```
python src\fetch_data.py
streamlit run app\app.py
```

## Origin
KadKaki is built on the
[Malaysian Credit Card Assistant v3.2](https://github.com/Pang512/malaysia-credit-card-rag/releases/tag/v3.2.0),
a portfolio project with its own evaluation results.

## Disclaimer
KadKaki provides information, not financial advice. Always confirm details with the bank before applying.