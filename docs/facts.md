# KadKaki: verified facts register

Facts about the outside world that KadKaki's code, data or user-facing text relies on.
Each one has its source and the date it was checked. Re-check before relying on anything
older than 3 months. **Tier 3 sources (news) are for discovery only: never cite them in the app.**

Last full review: 29 Oct 2026 (KK-07).

## Regulation

| # | Fact | Source (tier) | Checked | Status |
|---|---|---|---|---|
| R1 | A principal cardholder must be at least **21 years old** and earn at least **RM24,000 a year**. | BNM Policy Document on Credit Card and Credit Card-i, para 11.1, p. 10 (BNM; read by See Kyi) | 29 Oct 2026 | ✅ |
| R2 | A principal cardholder earning **RM36,000 a year or less** may hold credit cards from at most **two issuers**, with a limit of at most **2× monthly income per issuer**. Applies to **both existing and new** cardholders. | Same document, para 11.2 (a) and (b), p. 10 (BNM) | 29 Oct 2026 | ✅ |
| R3 | Supplementary cardholders: at least **18** (Hong Leong). The 21 minimum for principals is BNM's (R1); banks may set higher ages or incomes per card. | Hong Leong credit card FAQ (bank) | 29 Oct 2026 | ✅ Bank-specific: store per card |
| R4 | BNM's **Policy Document on Credit Card and Credit Card-i** (BNM/RH/PD 028-141) was issued **19 Dec 2025**. In force from that date, with some paragraphs from 1 Apr 2026, 1 Jun 2026 (new products) and 1 Jan 2027. It covers minimum age and income, minimum monthly repayment and disclosure. | Skrine legal alert, Jan 2026 (tier 3); the document itself on bnm.gov.my (BNM) | 29 Oct 2026 | ✅ Its income and issuer rules are R1 and R2 |

## Basic credit card (BCC)

| # | Fact | Source (tier) | Checked | Status |
|---|---|---|---|---|
| B1 | BCC: maximum **14% p.a.** interest or profit rate; **no rewards or cashback**; banks offer it **in phases from October 2026**; existing cardholders may switch and transfer eligible balances. | BNM press release "Belanjawan 2027", 9 Oct 2026 (BNM) | 29 Oct 2026 | ✅ |
| B2 | Reported BCC cards: **Alliance Bank Visa Basic** (14% since 1 Oct 2026; limit RM20,000 or 2× monthly income, whichever is lower), **Maybank Islamic Nadi Credit Card-i** (fixed 14%), **CIMB Lite-i** (fixed 14%), **RHB Sinar Credit Card-i**, **Bank Muamalat Awwal Credit Card-i** (launched 20 Oct 2026, no annual fee). | Fintech News Malaysia, 9 and 21 Oct 2026 (tier 3) | 29 Oct 2026 | ⚠️ Discovery only: verify each on the bank's own page in KK-11 to KK-13 |
| B3 | Nine banks (about 62% of the card market) are expected to offer BCC by November 2026. | Utusan Malaysia via Fintech News, Oct 2026 (tier 3) | 29 Oct 2026 | ⚠️ Expectation, not fact: re-check in December |

## Disclosure (PDS)

| # | Fact | Source (tier) | Checked | Status |
|---|---|---|---|---|
| D1 | BNM revised its **Policy Document on Product Transparency and Disclosure**: every PDS must fit in **two A4 pages**, use a **standardised template**, readable fonts and plain, active language. | Malay Mail, 27 May 2026; RinggitPlus, 25 May 2026 (both tier 3, reporting a BNM media workshop on 21 May 2026) | 29 Oct 2026 | ⚠️ **Open:** compliance date for credit cards not found |
| D2 | Hong Leong's live PDS is already in the short format: **"CC PDS ENG V OCT 2026"**, 9 cards on one sheet. | The PDS itself (bank) | 28 Oct 2026 | ✅ Shows banks are switching: expect most PDS links to change soon |

## Issuers

| # | Fact | Source (tier) | Checked | Status |
|---|---|---|---|---|
| I1 | BNM lists **26** credit card issuers (24 banks or Islamic banks, 2 non-banks: AEON Credit and Paydee). Full list in `data/issuers.yaml`. | BNM FSP Directory (BNM) | 29 Oct 2026 | ✅ Confirmed with the directory's Credit Card Issuers filter |
| I2 | Some Islamic arms are **not** listed as credit card issuers: Standard Chartered Saadiq, and Hong Leong Islamic, AmBank Islamic, Alliance Islamic and OCBC Al-Amin do not appear. Their Islamic cards may be issued through the parent bank. | BNM FSP Directory (BNM) | 29 Oct 2026 | ℹ️ Check who the issuer is on each Islamic card's PDS |

## Tools and limits

| # | Fact | Source | Checked |
|---|---|---|---|
| T1 | Gemini free tier, KadKaki project: 3.5 Flash-Lite 15 RPM / 500 RPD; 3.6 Flash 5 RPM / 20 RPD | Google AI Studio rate-limit page | 28 Oct 2026 |
| T2 | GitHub Free: **2,000** Actions minutes a month for private repos; free for public repos | GitHub Docs | 28 Oct 2026 |
| T3 | Scheduled workflows in public repos turn off after 60 days without activity | GitHub Docs | 28 Oct 2026 |
| T4 | Streamlit Community Cloud: one private app per workspace | Streamlit forum | 28 Oct 2026 |

## Sources
- BNM FSP Directory: https://www.bnm.gov.my/regulations/fsp-directory
- BNM "Belanjawan 2027" press release: https://www.bnm.gov.my/-/belanjawan27-bm
- BNM Policy Document on Credit Card and Credit Card-i (BNM/RH/PD 028-141, 19 Dec 2025): search the title on bnm.gov.my
- BNM 2011 credit card measures (background): https://www.bnm.gov.my/-/new-measures-on-credit-cards-to-promote-prudent-financial-management-and-responsible-business-practices
- Hong Leong credit card FAQ: https://www.hlb.com.my/en/personal-banking/help-support/product-faq/credit-card.html
- Skrine, BNM policy documents on payment cards: https://www.skrine.com/insights/alerts/january-2026-1/bank-negara-malaysia-issues-policy-documents-on-pa
- Fintech News, basic credit cards: https://fintechnews.my/61303/fintech-lending-malaysia/malaysia-basic-credit-cards-14-percent-budget-2027/
- Fintech News, Bank Muamalat Awwal: https://fintechnews.my/61740/banking/bank-muamalat-credit-card-14-percent-annual-rate/
- Malay Mail, PDS rules: https://www.malaymail.com/news/malaysia/2026/05/27/war-on-fine-print-bank-negara-uses-psychology-to-design-financial-documents-malaysians-might-actually-read/221456
- RinggitPlus, PDS rules: https://ringgitplus.com/en/blog/bank-news/bank-negara-malaysia-revises-financial-product-disclosure-standards.html
