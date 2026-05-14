# Financial Statement Analyzer — Project Context

## Project Overview
An AI-powered financial analysis engine — works for ANY publicly listed company.
- Enter a company name, ticker symbol, or CIK number
- Engine fetches live data, computes all ratios and signals
- AI writes structured commentary from signals only (never from raw data)
- Live app: https://financial-statement-analyzer-msafinancials.streamlit.app/
- GitHub: https://github.com/ansarisaad418/financial-statement-analyzer

---

## File Structure
- engine.py — fetches data, normalizes, computes ratios, generates signals, outputs JSON
- app.py — Streamlit frontend with company search input
- interpreter.py — calls Gemini API for narrative commentary
- .streamlit/secrets.toml — API keys

---

## Current State

### Phase 2 status: ALMOST DONE — one blocker remaining

The FMP API integration is complete and deployed to GitHub. However:
- FMP free tier returns 403 Forbidden on financial statement endpoints
- Decision made: SWITCH TO YFINANCE (free, no API key needed)
- yfinance is NOT yet implemented — this is the next task

### What needs to be done in the next session (ONE TASK):
Replace the FMP data-fetching layer in engine.py with yfinance.

Specifically, only these two functions change in engine.py:
1. load_all_statements(ticker) — currently calls FMP API, needs to call yfinance instead
2. normalize() — currently maps FMP field names, needs to map yfinance field names

Everything from calculate_metrics() onward is UNTOUCHED.

Also in app.py: keep the FMP API key field in the sidebar (user wants it) but it will be unused.
Remove FMP_API_KEY from engine.py globals since yfinance needs no key.
Keep search_company() and resolve_cik() as stubs or remove them — TBD.

---

## Architecture (unchanged)
TICKER/CIK INPUT
  -> load_all_statements(ticker)   [NEEDS REWRITE: yfinance instead of FMP]
  -> normalize()                   [NEEDS REWRITE: yfinance fields -> internal names]
  -> calculate_metrics()           [UNTOUCHED]
  -> generate_signals()            [UNTOUCHED]
  -> build_output()                [UNTOUCHED]
  -> AI commentary                 [UNTOUCHED]

---

## Internal field names (normalize() must output these — DO NOT CHANGE)
revenue, cogs, rd_expense, sga, amortization, restructuring, integration_costs,
equity_earnings, sundry_income, interest_income, interest_expense, ebt, tax,
net_income, net_income_dow,
cash, trade_receivables, inventories, total_current_assets, net_property, goodwill,
total_assets, total_current_liabilities, long_term_debt, ltd_current, notes_payable,
pension_liability, total_equity, dow_equity, retained_earnings,
cfo, capex, depreciation_amort, dividends_paid, buybacks

## yfinance field reference (for the next session)
yfinance Ticker object: import yfinance as yf; t = yf.Ticker("AAPL")
- t.financials         -> Income Statement (columns = dates, rows = line items)
- t.balance_sheet      -> Balance Sheet
- t.cashflow           -> Cash Flow Statement
- All are pandas DataFrames, columns are Timestamps (use .year to get int year)
- Values are in actual dollars — divide by 1,000,000 for millions

Key yfinance row labels:
Income Statement:
  "Total Revenue"                    -> revenue
  "Cost Of Revenue"                  -> cogs
  "Research And Development"         -> rd_expense
  "Selling General Administrative"   -> sga
  "Reconciled Depreciation"          -> amortization (use or default 0)
  "Interest Expense"                 -> interest_expense (negate — yf shows negative)
  "Interest Income"                  -> interest_income
  "Pretax Income"                    -> ebt
  "Tax Provision"                    -> tax
  "Net Income"                       -> net_income and net_income_dow

Balance Sheet:
  "Cash And Cash Equivalents"        -> cash
  "Accounts Receivable"              -> trade_receivables
  "Inventory"                        -> inventories
  "Current Assets"                   -> total_current_assets
  "Net PPE"                          -> net_property
  "Goodwill"                         -> goodwill
  "Total Assets"                     -> total_assets
  "Current Liabilities"              -> total_current_liabilities
  "Long Term Debt"                   -> long_term_debt
  "Current Debt"                     -> notes_payable (set ltd_current=0)
  "Stockholders Equity"              -> total_equity AND dow_equity
  "Retained Earnings"                -> retained_earnings

Cash Flow:
  "Operating Cash Flow"              -> cfo
  "Capital Expenditure"              -> capex (yf shows negative — engine expects negative, OK)
  "Depreciation And Amortization"    -> depreciation_amort
  "Common Stock Dividend Paid"       -> dividends_paid (yf shows negative — OK)
  "Repurchase Of Capital Stock"      -> buybacks (yf shows negative — OK)

## Signals (13 active, all in generate_signals())
fcf_conversion, non_core_income, net_debt_to_ebitda, capital_allocation,
restructuring, current_ratio, operating_leverage, margin_driver,
leverage_coverage_interaction, revenue_cagr, fcf_trend, leverage_trend,
dividend_sustainability

---

## API Keys
- Gemini: .streamlit/secrets.toml as GEMINI_API_KEY = "AIzaSyA0cMj7D_CA86xJEd0buajNY_AVGL5yuqc"
- FMP: kept in sidebar UI but no longer used by engine after yfinance switch

---

## Working Constraints — READ CAREFULLY
- Do NOT scan or analyze the full repository unless specific code is shared
- Ask for specific code sections only when necessary
- Minimal targeted fixes only — no rewrites
- No code-native background — explain before changing
- Always syntax-check after edits
- Ask questions one by one when needed
- Always present file links after changes

---

## Deployment
- Streamlit Cloud app: https://financial-statement-analyzer-msafinancials.streamlit.app/
- GitHub: https://github.com/ansarisaad418/financial-statement-analyzer
- After yfinance implementation: git add engine.py requirements.txt, commit, push
- Add yfinance to requirements.txt (remove openpyxl if desired)
