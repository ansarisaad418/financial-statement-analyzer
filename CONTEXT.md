# Financial Statement Analyzer — Project Context

## Project Overview
An AI-powered financial analysis engine — works for ANY publicly listed company.
- Enter a company name, ticker symbol, or CIK number
- Engine fetches live data from FMP API, computes all ratios and signals
- AI writes structured commentary from signals only (never from raw data)
- Live app: https://financial-statement-analyzer-msafinancials.streamlit.app/
- GitHub: https://github.com/ansarisaad418/financial-statement-analyzer

---

## File Structure
- engine.py — fetches FMP data, normalizes, computes ratios, generates signals, outputs JSON
- app.py — Streamlit frontend with company search input
- interpreter.py — calls Gemini API for narrative commentary
- .streamlit/secrets.toml — API keys (Gemini + FMP)

---

## Current State (Phase 2 Complete)

### Data Source
- FMP API (Financial Modeling Prep) — replaces Excel
- Any publicly listed company by ticker, name, or CIK
- Up to 10 years of annual data per company
- Values returned in USD (divided by 1,000,000 — pipeline stays in millions)

### Architecture
TICKER/CIK INPUT
  -> load_all_statements(ticker)   [FMP API fetch]
  -> normalize()                   [FMP fields -> internal names]
  -> calculate_metrics()           [unchanged]
  -> generate_signals()            [unchanged]
  -> build_output()                [company/ticker now dynamic]
  -> AI commentary                 [unchanged]

### Key FMP Field Mappings (normalize)
revenue             <- revenue
cogs                <- costOfRevenue
rd_expense          <- researchAndDevelopmentExpenses (or 0)
sga                 <- sellingGeneralAndAdministrativeExpenses
amortization        <- depreciationAndAmortization IS (or 0)
interest_expense    <- interestExpense
ebt                 <- incomeBeforeTax
net_income_dow      <- netIncome
cash                <- cashAndCashEquivalents
inventories         <- inventory
long_term_debt      <- longTermDebt
notes_payable       <- shortTermDebt (or 0)
ltd_current         <- 0 (bundled into shortTermDebt)
dow_equity          <- totalStockholdersEquity
cfo                 <- operatingCashFlow
capex               <- capitalExpenditure (negative in FMP)
depreciation_amort  <- depreciationAndAmortization CF
dividends_paid      <- dividendsPaid (negative in FMP)
buybacks            <- commonStockRepurchased (negative in FMP)

### Signals (13 active)
fcf_conversion, non_core_income, net_debt_to_ebitda, capital_allocation,
restructuring, current_ratio, operating_leverage, margin_driver,
leverage_coverage_interaction, revenue_cagr, fcf_trend, leverage_trend,
dividend_sustainability

Note: restructuring and non_core_income signals will not fire for most companies
(FMP does not separately report these line items). All other signals fire normally.

---

## API Keys
- Gemini: .streamlit/secrets.toml as GEMINI_API_KEY
- FMP: .streamlit/secrets.toml as FMP_API_KEY
- Both keys also readable from sidebar if secrets file is absent

---

## Working Constraints — READ CAREFULLY
- Do NOT scan or analyze the full repository unless specific code is shared
- Ask for specific code sections only when necessary
- Minimal targeted fixes only — no rewrites
- Teach where things live in the code before changing them
- No code-native background — explain before changing
- Always syntax-check after edits
- Always present the final file for download after changes

---

## Deployment Checklist (next step)
1. git add engine.py app.py interpreter.py requirements.txt CONTEXT.md .streamlit/secrets.toml
2. git commit -m "Phase 2: FMP API integration — multi-company support"
3. git push origin main
4. On Streamlit Cloud -> Settings -> Secrets -> add FMP_API_KEY = your key
5. Redeploy

---

## Next Phase Ideas
- Peer comparison: analyze 2-3 companies side by side
- Sector benchmarking: compare ratios vs industry medians
- Export to PDF report
- RAG layer: MD&A retrieval for grounded insights
