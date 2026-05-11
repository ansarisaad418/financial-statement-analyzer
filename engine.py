"""
Financial Statement Analyzer - Engine
Company: Dow Inc.
Data:2019, 2020, 2021, 2022 (from 2023 10-K)
 
Pipeline:
  1. Load raw Excel data
  2. Normalize (map Dow's labels → standard names)
  3. Calculate metrics (margins, liquidity, leverage, efficiency, cash quality)
  4. Generate signals (rule-based flags)
  5. Output structured JSON → ready for AI interpretation
"""
 
import pandas as pd
import json
import math
 
# ── CONFIG ────────────────────────────────────────────────────────────────────
 
FILE_PATH = "FinAnalyst.xlsx"
YEARS = []  # auto-populated by load_all_statements()
 
# ── STEP 1: LOAD RAW DATA ─────────────────────────────────────────────────────
 
def load_statement(sheet_name, year_columns):
    """
    Reads a sheet and returns a dict: {row_label: {year: value}}
 
    After the Excel cleanup, all three sheets share the same clean structure:
      - Row 0 is a header row containing year values (2022, 2021, 2020)
      - Column 0 always contains row labels
      - Year values appear either as integer column headers OR
        as values in row 0 of an Unnamed column
 
    Strategy:
      1. Find which columns contain the year values (either as headers or row-0 values)
      2. Use column 0 as the label column
      3. For each data row, read the value from the year column
    """
    # Read with no header first to inspect row 0
    df_raw = pd.read_excel(FILE_PATH, sheet_name=sheet_name, header=None)
 
    # Find which row contains the year labels (scan first 3 rows)
    year_col_map = {}  # year_int → col_index
    header_row = None
    for row_idx in range(min(3, len(df_raw))):
        row_vals = df_raw.iloc[row_idx].tolist()
        for col_idx, val in enumerate(row_vals):
            try:
                v = int(float(str(val).replace(",", "").strip()))
                if v in year_columns:
                    year_col_map[v] = col_idx
                    header_row = row_idx
            except (ValueError, TypeError):
                pass
        if year_col_map:
            break
 
    # Data starts after the header row
    data_start = (header_row + 1) if header_row is not None else 1
    label_col_idx = 0
 
    def clean_val(val):
        try:
            cleaned = (str(val)
                       .replace(",", "")
                       .replace("$", "")
                       .replace("\xa0", "")
                       .replace("\u00a0", "")
                       .replace(" ", "")
                       .replace("—", "")
                       .strip())
            if cleaned in ("", "nan", "None", "-"):
                return None
            v = float(cleaned)
            return None if math.isnan(v) else v
        except (ValueError, TypeError):
            return None
 
    result = {}
    for row_idx in range(data_start, len(df_raw)):
        row = df_raw.iloc[row_idx]
        label = str(row[label_col_idx]).strip()
        if label in ("", "nan", "None"):
            continue
        values = {}
        for year, col_idx in year_col_map.items():
            values[year] = clean_val(row[col_idx])
        result[label] = values
 
    detected_years = sorted(year_col_map.keys(), reverse=True)
    return result, detected_years
 
 
def load_all_statements():
    global YEARS
    income, detected = load_statement("Income Statement", list(range(2015, 2030)))
    YEARS = detected
    balance, _ = load_statement("Balance Sheet", YEARS)
    cashflow, _ = load_statement("Cash Flow Statement", YEARS)
    return income, balance, cashflow
 
 
# ── STEP 2: NORMALIZE ─────────────────────────────────────────────────────────
 
def get(data, label, year):
    """Safe lookup — returns None if label or year missing."""
    return data.get(label, {}).get(year, None)
 
 
def normalize(income, balance, cashflow):
    """
    Maps Dow's exact SEC labels to clean standard names.
    Returns a dict structured as: {year: {metric: value}}
    Only uses years where balance sheet data exists (2021, 2022).
    For income + cashflow, all 3 years are available.
    """
    normalized = {}
 
    for year in YEARS:
        # ── Income Statement ──────────────────────────────────────────────────
        revenue         = get(income, "Net sales", year)
        cogs            = get(income, "Cost of sales", year)
        rd_expense      = get(income, "Research and development expenses", year)
        sga             = get(income, "Selling, general and administrative expenses", year)
        amortization    = get(income, "Amortization of intangibles", year)
        restructuring   = get(income, "Restructuring and asset related charges - net", year)
        integration     = get(income, "Integration and separation costs", year)
 
        # Non-core items — quarantined from margin calculations
        equity_earnings = get(income, "Equity in earnings (losses) of nonconsolidated affiliates", year)
        sundry          = get(income, "Sundry income (expense) - net", year)
 
        interest_income  = get(income, "Interest income", year)
        interest_expense = get(income, "Interest expense and amortization of debt discount", year)
        ebt              = get(income, "Income before income taxes", year)
        tax              = get(income, "Provision for income taxes", year)
        net_income       = get(income, "Net income", year)
        net_income_dow   = get(income, "Net income available for Dow Inc. common stockholders", year)
 
        # ── Balance Sheet (2018 2019 2020 2021 2022) ───────────────────────────────
        if year in [2022, 2021, 2020, 2019, 2018]:
            cash              = get(balance, "Cash and cash equivalents", year)
            trade_receivables = get(balance, "Trade (net of allowance for doubtful receivables - 2022: $110; 2021: $54)", year)
            other_receivables = get(balance, "Other", year)
            inventories       = get(balance, "Inventories", year)
            other_current     = get(balance, "Other current assets", year)
            total_current_assets = get(balance, "Total current assets", year)
 
            net_property      = get(balance, "Net property", year)
            goodwill          = get(balance, "Goodwill", year)
            total_assets      = get(balance, "Total Assets", year)
 
            total_current_liabilities = get(balance, "Total current liabilities", year)
            long_term_debt    = get(balance, "Long-Term Debt", year)
            ltd_current       = get(balance, "Long-term debt due within one year", year)
            notes_payable     = get(balance, "Notes payable", year)
            pension_liability = get(balance, "Pension and other postretirement benefits - noncurrent", year)
            total_equity      = get(balance, "Total equity", year)
            dow_equity = get(balance, "Dow Inc.\u2019s stockholders\u2019 equity", year)
            retained_earnings = get(balance, "Retained earnings", year)
        else:
            # 2020 balance sheet not available
            cash = trade_receivables = other_receivables = inventories = None
            other_current = total_current_assets = net_property = goodwill = None
            total_assets = total_current_liabilities = long_term_debt = None
            ltd_current = notes_payable = pension_liability = None
            total_equity = dow_equity = retained_earnings = None
 
        # ── Cash Flow Statement ───────────────────────────────────────────────
        cfo               = get(cashflow, "Cash provided by operating activities", year)
        capex             = get(cashflow, "Capital expenditures", year)
        depreciation_amort = get(cashflow, "Depreciation and amortization", year)
        dividends_paid    = get(cashflow, "Dividends paid to stockholders", year)
        buybacks          = get(cashflow, "Purchases of treasury stock", year)
 
        normalized[year] = {
            # Income Statement
            "revenue":              revenue,
            "cogs":                 cogs,
            "rd_expense":           rd_expense,
            "sga":                  sga,
            "amortization":         amortization,
            "restructuring":        restructuring,
            "integration_costs":    integration,
            "equity_earnings":      equity_earnings,       # non-core
            "sundry_income":        sundry,                # non-core
            "interest_income":      interest_income,
            "interest_expense":     interest_expense,
            "ebt":                  ebt,
            "tax":                  tax,
            "net_income":           net_income,
            "net_income_dow":       net_income_dow,
            # Balance Sheet
            "cash":                 cash,
            "trade_receivables":    trade_receivables,
            "inventories":          inventories,
            "total_current_assets": total_current_assets,
            "net_property":         net_property,
            "goodwill":             goodwill,
            "total_assets":         total_assets,
            "total_current_liabilities": total_current_liabilities,
            "long_term_debt":       long_term_debt,
            "ltd_current":          ltd_current,
            "notes_payable":        notes_payable,
            "pension_liability":    pension_liability,
            "total_equity":         total_equity,
            "dow_equity":           dow_equity,
            "retained_earnings":    retained_earnings,
            # Cash Flow
            "cfo":                  cfo,
            "capex":                capex,
            "depreciation_amort":   depreciation_amort,
            "dividends_paid":       dividends_paid,
            "buybacks":             buybacks,
        }
 
    return normalized
 
 
# ── STEP 3: CALCULATE METRICS ─────────────────────────────────────────────────
 
def safe_divide(numerator, denominator):
    """Returns None if either value is None or denominator is zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
 
 
def calculate_metrics(normalized):
    """
    Computes all financial ratios and derived metrics.
    Returns {year: {metric_name: value}}
    """
    metrics = {}
 
    for year, d in normalized.items():
 
        # ── Profitability ─────────────────────────────────────────────────────
 
        gross_profit = (d["revenue"] - d["cogs"]) if d["revenue"] is not None and d["cogs"] is not None else None
        gross_margin = safe_divide(gross_profit, d["revenue"])
 
        # Core EBIT — excludes non-core items (equity earnings, sundry)
        # Formula: Revenue - COGS - R&D - SG&A - Amortization - Restructuring
        core_operating_income = None
        if all(v is not None for v in [d["revenue"], d["cogs"], d["rd_expense"], d["sga"], d["amortization"]]):
            core_operating_income = (
                d["revenue"]
                - d["cogs"]
                - d["rd_expense"]
                - d["sga"]
                - d["amortization"]
                - (d["restructuring"] or 0)
                - (d["integration_costs"] or 0)
            )
 
        core_operating_margin = safe_divide(core_operating_income, d["revenue"])
 
        # Reported EBIT (includes non-core — useful for comparison)
        reported_ebit = None
        if d["ebt"] is not None and d["interest_expense"] is not None:
            reported_ebit = d["ebt"] + d["interest_expense"] - (d["interest_income"] or 0)
 
        reported_ebit_margin = safe_divide(reported_ebit, d["revenue"])
        net_margin = safe_divide(d["net_income_dow"], d["revenue"])
 
        # EBITDA (core operating income + D&A)
        ebitda = None
        if core_operating_income is not None and d["depreciation_amort"] is not None:
            ebitda = core_operating_income + d["depreciation_amort"]
        ebitda_margin = safe_divide(ebitda, d["revenue"])
 
        # Non-core income as % of reported pre-tax income — measures dependency
        non_core_total = (d["equity_earnings"] or 0) + (d["sundry_income"] or 0)
        non_core_as_pct_ebt = safe_divide(non_core_total, d["ebt"]) if d["ebt"] is not None else None
 
        # ── Cash Quality ──────────────────────────────────────────────────────
        fcf = None
        if d["cfo"] is not None and d["capex"] is not None:
            fcf = d["cfo"] + d["capex"]  # capex is already negative in the data
 
        fcf_conversion = safe_divide(fcf, d["net_income_dow"])
        cfo_conversion = safe_divide(d["cfo"], d["net_income_dow"])
 
        # ── Liquidity (balance sheet years only) ─────────────────────────────
        current_ratio = safe_divide(d["total_current_assets"], d["total_current_liabilities"])
 
        # Quick ratio = (Current Assets - Inventories) / Current Liabilities
        quick_ratio = None
        if d["total_current_assets"] is not None and d["inventories"] is not None and d["total_current_liabilities"] is not None:
            quick_ratio = round((d["total_current_assets"] - d["inventories"]) / d["total_current_liabilities"], 4)
 
        # ── Leverage ──────────────────────────────────────────────────────────
        total_debt = None
        if d["long_term_debt"] is not None and d["ltd_current"] is not None and d["notes_payable"] is not None:
            total_debt = d["long_term_debt"] + d["ltd_current"] + d["notes_payable"]
 
        net_debt = None
        if total_debt is not None and d["cash"] is not None:
            net_debt = total_debt - d["cash"]
 
        net_debt_to_ebitda = safe_divide(net_debt, ebitda)
        debt_to_equity = safe_divide(total_debt, d["dow_equity"])
 
        interest_coverage = safe_divide(core_operating_income, d["interest_expense"])
 
        # ── Efficiency ────────────────────────────────────────────────────────
        asset_turnover = safe_divide(d["revenue"], d["total_assets"])
 
        # ── Shareholder Returns ───────────────────────────────────────────────
        total_cash_returned = None
        if d["dividends_paid"] is not None and d["buybacks"] is not None:
            # Both are negative in the cash flow statement
            total_cash_returned = abs(d["dividends_paid"]) + abs(d["buybacks"])
 
        cash_returned_vs_fcf = safe_divide(total_cash_returned, fcf) if fcf is not None else None
 
        # ── DuPont (5-factor) — balance sheet years only ──────────────────────
        # ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Leverage
        tax_burden       = safe_divide(d["net_income_dow"], d["ebt"])
        interest_burden  = safe_divide(d["ebt"], reported_ebit)
        leverage_factor  = safe_divide(d["total_assets"], d["dow_equity"])
        roe_dupont       = None
        if all(v is not None for v in [tax_burden, interest_burden, core_operating_margin, asset_turnover, leverage_factor]):
            roe_dupont = round(tax_burden * interest_burden * core_operating_margin * asset_turnover * leverage_factor, 4)
 
        roe_simple = safe_divide(d["net_income_dow"], d["dow_equity"])
 
        metrics[year] = {
            # Profitability
            "gross_profit":             round(gross_profit, 1) if gross_profit is not None else None,
            "gross_margin":             gross_margin,
            "core_operating_income":    round(core_operating_income, 1) if core_operating_income is not None else None,
            "core_operating_margin":    core_operating_margin,
            "reported_ebit":            round(reported_ebit, 1) if reported_ebit is not None else None,
            "reported_ebit_margin":     reported_ebit_margin,
            "net_margin":               net_margin,
            "ebitda":                   round(ebitda, 1) if ebitda is not None else None,
            "ebitda_margin":            ebitda_margin,
            "non_core_as_pct_ebt":      non_core_as_pct_ebt,
 
            # Cash Quality
            "fcf":                      round(fcf, 1) if fcf is not None else None,
            "fcf_conversion":           fcf_conversion,
            "cfo_conversion":           cfo_conversion,
 
            # Liquidity
            "current_ratio":            current_ratio,
            "quick_ratio":              quick_ratio,
 
            # Leverage
            "total_debt":               round(total_debt, 1) if total_debt is not None else None,
            "net_debt":                 round(net_debt, 1) if net_debt is not None else None,
            "net_debt_to_ebitda":       net_debt_to_ebitda,
            "debt_to_equity":           debt_to_equity,
            "interest_coverage":        interest_coverage,
 
            # Efficiency
            "asset_turnover":           asset_turnover,
            "revenue":                  d["revenue"],
 
            # Shareholder Returns
            "total_cash_returned":      round(total_cash_returned, 1) if total_cash_returned is not None else None,
            "cash_returned_vs_fcf":     cash_returned_vs_fcf,
 
            # DuPont
            "roe_simple":               roe_simple,
            "roe_dupont":               roe_dupont,
            "dupont_tax_burden":        tax_burden,
            "dupont_interest_burden":   interest_burden,
            "dupont_leverage_factor":   leverage_factor,
        
        }
 
    return metrics
 
 
# ── STEP 4: GENERATE SIGNALS ──────────────────────────────────────────────────
 
def generate_signals(metrics, normalized):
    """
    Rule-based signal detection. Each signal has:
      - metric: what is being measured
      - signal: POSITIVE / NEGATIVE / WATCH / NEUTRAL
      - severity: HIGH / MEDIUM / LOW
      - finding: plain English description of what the rule found
    """
    signals = []
 
    def add(metric, signal, severity, finding):
        signals.append({
            "metric": metric,
            "signal": signal,
            "severity": severity,
            "finding": finding
        })
 
    m22, m21, m20 = metrics.get(2022), metrics.get(2021), metrics.get(2020)
 
    # ── FCF Conversion ────────────────────────────────────────────────────────
    if m22 and m22["fcf_conversion"] is not None:
        fcf_conv = m22["fcf_conversion"]
        if fcf_conv < 0.75:
            add("fcf_conversion", "NEGATIVE", "HIGH",
                f"FCF conversion in 2022 is {fcf_conv:.1%} — below the 75% threshold. Earnings quality is weak; cash generation is not keeping pace with reported profit.")
        elif fcf_conv >= 0.75 and fcf_conv < 1.0:
            add("fcf_conversion", "WATCH", "LOW",
                f"FCF conversion in 2022 is {fcf_conv:.1%}. Acceptable but below 1x — some earnings are not converting to cash.")
        else:
            add("fcf_conversion", "POSITIVE", "LOW",
                f"FCF conversion in 2022 is {fcf_conv:.1%} — above 1x, indicating strong earnings quality.")
 
    # ── Non-Core Income Dependency ────────────────────────────────────────────
    for year, m in [(2022, m22), (2021, m21), (2020, m20)]:
        if m and m["non_core_as_pct_ebt"] is not None:
            pct = m["non_core_as_pct_ebt"]
            if abs(pct) > 0.20:
                add("non_core_income", "WATCH", "MEDIUM",
                    f"In {year}, non-core items (equity earnings + sundry) represented {pct:.1%} of pre-tax income. Reported earnings are sensitive to volatile, non-operational items.")
 
    # ── Leverage ──────────────────────────────────────────────────────────────
    if m22 and m22["net_debt_to_ebitda"] is not None:
        nd_ebitda = m22["net_debt_to_ebitda"]
        if nd_ebitda > 3.0:
            add("net_debt_to_ebitda", "NEGATIVE", "HIGH",
                f"Net Debt/EBITDA of {nd_ebitda:.1f}x in 2022 is elevated. Leverage above 3x raises refinancing and covenant risk.")
        elif nd_ebitda > 2.0:
            add("net_debt_to_ebitda", "WATCH", "MEDIUM",
                f"Net Debt/EBITDA of {nd_ebitda:.1f}x in 2022 is moderate. Manageable but leaves limited headroom in a downturn.")
        else:
            add("net_debt_to_ebitda", "POSITIVE", "LOW",
                f"Net Debt/EBITDA of {nd_ebitda:.1f}x in 2022 is conservative.")
 
    # ── Shareholder Return vs FCF ─────────────────────────────────────────────
    if m22 and m22["cash_returned_vs_fcf"] is not None:
        cr_fcf = m22["cash_returned_vs_fcf"]
        if cr_fcf > 1.0:
            add("capital_allocation", "NEGATIVE", "HIGH",
                f"In 2022, Dow returned {cr_fcf:.1%} of FCF to shareholders (dividends + buybacks). Returning more cash than generated — funded by debt or asset sales.")
        elif cr_fcf > 0.75:
            add("capital_allocation", "WATCH", "MEDIUM",
                f"In 2022, Dow returned {cr_fcf:.1%} of FCF to shareholders. Aggressive but sustainable if FCF holds.")
        else:
            add("capital_allocation", "POSITIVE", "LOW",
                f"In 2022, Dow returned {cr_fcf:.1%} of FCF to shareholders — retaining capital for reinvestment.")
 
    # ── Restructuring Recurrence ──────────────────────────────────────────────
    restructuring_years = []
    for year, data in normalized.items():
        val = data.get("restructuring")
        if val is not None and val > 0:
            restructuring_years.append(year)
    if len(restructuring_years) >= 2:
        add("restructuring", "WATCH", "MEDIUM",
            f"Restructuring charges appear in {len(restructuring_years)} out of {len(YEARS)} years ({', '.join(str(y) for y in sorted(restructuring_years, reverse=True))}). Recurring 'non-recurring' charges are an earnings quality red flag.")
 
    # ── Liquidity ─────────────────────────────────────────────────────────────
    if m22 and m22["current_ratio"] is not None:
        cr = m22["current_ratio"]
        if cr < 1.0:
            add("current_ratio", "NEGATIVE", "HIGH",
                f"Current ratio of {cr:.2f}x in 2022 — current liabilities exceed current assets. Short-term liquidity risk.")
        elif cr < 1.5:
            add("current_ratio", "WATCH", "LOW",
                f"Current ratio of {cr:.2f}x in 2022 is adequate but lean.")
        else:
            add("current_ratio", "POSITIVE", "LOW",
                f"Current ratio of {cr:.2f}x in 2022 is comfortable.")
 
 
    # ── COMPOSITION SIGNAL 1: Operating Leverage ─────────────────────────────
    # If revenue grows but operating income grows slower → cost pressure
    n20 = normalized.get(2020, {})
    n21 = normalized.get(2021, {})
    n22 = normalized.get(2022, {})
 
    rev20, rev21, rev22 = n20.get("revenue"), n21.get("revenue"), n22.get("revenue")
    oi20 = m20["core_operating_income"] if m20 else None
    oi21 = m21["core_operating_income"] if m21 else None
    oi22 = m22["core_operating_income"] if m22 else None
 
    if all(v is not None for v in [rev21, rev22, oi21, oi22]) and rev21 != 0 and oi21 != 0:
        rev_growth = (rev22 - rev21) / abs(rev21)
        oi_growth  = (oi22 - oi21) / abs(oi21)
        if rev_growth > 0 and oi_growth < rev_growth * 0.5:
            add("operating_leverage", "NEGATIVE", "HIGH",
                f"Revenue grew {rev_growth:.1%} from 2021 to 2022 but core operating income declined {oi_growth:.1%}. "
                f"Costs are growing faster than revenue — negative operating leverage.")
        elif rev_growth > 0 and oi_growth > rev_growth:
            add("operating_leverage", "POSITIVE", "LOW",
                f"Core operating income grew {oi_growth:.1%} — faster than revenue growth of {rev_growth:.1%}. "
                f"Positive operating leverage: the business is scaling efficiently.")
        elif rev_growth > 0 and oi_growth < 0:
            add("operating_leverage", "NEGATIVE", "HIGH",
                f"Revenue grew {rev_growth:.1%} from 2021 to 2022 but core operating income contracted {abs(oi_growth):.1%}. "
                f"Margin compression is absorbing all top-line growth.")
 
    # ── COMPOSITION SIGNAL 2: Margin Driver Decomposition ────────────────────
    # Gross margin stable but operating margin falling → SG&A/overhead problem
    if m21 and m22:
        gm21 = m21.get("gross_margin")
        gm22 = m22.get("gross_margin")
        om21 = m21.get("core_operating_margin")
        om22 = m22.get("core_operating_margin")
 
        if all(v is not None for v in [gm21, gm22, om21, om22]):
            gm_change = gm22 - gm21
            om_change = om22 - om21
 
            if abs(gm_change) < 0.01 and om_change < -0.02:
                add("margin_driver", "NEGATIVE", "MEDIUM",
                    f"Gross margin held relatively stable ({gm21:.1%} → {gm22:.1%}) while core operating margin "
                    f"fell from {om21:.1%} to {om22:.1%}. The margin pressure originates below the gross profit line — "
                    f"likely SG&A or overhead cost inflation, not raw material or production cost.")
            elif gm_change < -0.02 and om_change < -0.02:
                add("margin_driver", "NEGATIVE", "HIGH",
                    f"Both gross margin ({gm21:.1%} → {gm22:.1%}) and core operating margin ({om21:.1%} → {om22:.1%}) "
                    f"deteriorated. Margin pressure is broad-based — affecting both production costs and operating expenses.")
            elif gm_change < -0.02 and abs(om_change) < 0.01:
                add("margin_driver", "POSITIVE", "LOW",
                    f"Gross margin declined ({gm21:.1%} → {gm22:.1%}) but operating margin held stable ({om21:.1%} → {om22:.1%}). "
                    f"Management absorbed input cost pressure through SG&A discipline.")
 
    # ── COMPOSITION SIGNAL 3: Leverage + Coverage Interaction ────────────────
    # Rising debt AND falling coverage = compounded risk
    if m21 and m22:
        nd21 = m21.get("net_debt_to_ebitda")
        nd22 = m22.get("net_debt_to_ebitda")
        ic21 = m21.get("interest_coverage")
        ic22 = m22.get("interest_coverage")
 
        if all(v is not None for v in [nd21, nd22, ic21, ic22]):
            leverage_rising  = nd22 > nd21 * 1.05
            coverage_falling = ic22 < ic21 * 0.95
 
            if leverage_rising and coverage_falling:
                add("leverage_coverage_interaction", "NEGATIVE", "HIGH",
                    f"Net Debt/EBITDA rose from {nd21:.1f}x to {nd22:.1f}x while interest coverage fell from "
                    f"{ic21:.1f}x to {ic22:.1f}x. Rising leverage combined with declining coverage is a compounded "
                    f"credit risk signal — the company is taking on more debt while its ability to service it weakens.")
            elif not leverage_rising and not coverage_falling:
                add("leverage_coverage_interaction", "POSITIVE", "LOW",
                    f"Net Debt/EBITDA moved from {nd21:.1f}x to {nd22:.1f}x and interest coverage from {ic21:.1f}x "
                    f"to {ic22:.1f}x. Leverage and coverage are moving in a constructive direction.")
    # ── Pull all 5 years ──────────────────────────────────────────────────────
    m18 = metrics.get(2018)
    m19 = metrics.get(2019)
    all_years = [2018, 2019, 2020, 2021, 2022]
    all_m = {2018: m18, 2019: m19, 2020: m20, 2021: m21, 2022: m22}
 
    # ── 5-Year Margin Trend (replaces 3-year) ─────────────────────────────────
    margin_5yr = [(y, all_m[y]["core_operating_margin"])
                  for y in all_years
                  if all_m[y] and all_m[y].get("core_operating_margin") is not None]
    if len(margin_5yr) >= 4:
        vals = [v for _, v in margin_5yr]
        yrs  = [y for y, _ in margin_5yr]
        if all(vals[i] < vals[i-1] for i in range(1, len(vals))):
            add("core_operating_margin_5yr", "NEGATIVE", "HIGH",
                f"Core operating margin has deteriorated every year for {len(vals)} consecutive years: "
                f"{' → '.join(f'{v:.1%}' for v in vals)} ({yrs[0]}–{yrs[-1]}).")
        elif vals[-1] < vals[-2] and vals[-2] == max(vals):
            add("core_operating_margin_5yr", "WATCH", "MEDIUM",
                f"Core operating margin peaked at {vals[-2]:.1%} in {yrs[-2]} and has since contracted to "
                f"{vals[-1]:.1%} in {yrs[-1]}, despite improvement in prior years.")
 
    # ── Leverage Trend (5-year) ───────────────────────────────────────────────
    nd_5yr = [(y, all_m[y]["net_debt_to_ebitda"])
              for y in all_years
              if all_m[y] and all_m[y].get("net_debt_to_ebitda") is not None]
    if len(nd_5yr) >= 3:
        nd_vals = [v for _, v in nd_5yr]
        nd_yrs  = [y for y, _ in nd_5yr]
        if all(nd_vals[i] > nd_vals[i-1] for i in range(1, len(nd_vals))):
            add("leverage_trend", "NEGATIVE", "HIGH",
                f"Net Debt/EBITDA has risen every year for {len(nd_vals)} consecutive years: "
                f"{' → '.join(f'{v:.1f}x' for v in nd_vals)} ({nd_yrs[0]}–{nd_yrs[-1]}). "
                f"Sustained leverage expansion is a structural risk.")
        elif all(nd_vals[i] < nd_vals[i-1] for i in range(1, len(nd_vals))):
            add("leverage_trend", "POSITIVE", "LOW",
                f"Net Debt/EBITDA has declined consistently: "
                f"{' → '.join(f'{v:.1f}x' for v in nd_vals)} ({nd_yrs[0]}–{nd_yrs[-1]}). "
                f"Sustained deleveraging is a strong balance sheet signal.")
 
    # ── Interest Coverage Trend (5-year) ─────────────────────────────────────
    ic_5yr = [(y, all_m[y]["interest_coverage"])
              for y in all_years
              if all_m[y] and all_m[y].get("interest_coverage") is not None]
    if len(ic_5yr) >= 3:
        ic_vals = [v for _, v in ic_5yr]
        ic_yrs  = [y for y, _ in ic_5yr]
        if all(ic_vals[i] < ic_vals[i-1] for i in range(1, len(ic_vals))):
            add("interest_coverage_trend", "NEGATIVE", "HIGH",
                f"Interest coverage has declined every year: "
                f"{' → '.join(f'{v:.1f}x' for v in ic_vals)} ({ic_yrs[0]}–{ic_yrs[-1]}). "
                f"Sustained erosion of debt service capacity.")
        elif ic_vals[-1] < ic_vals[-2] and max(ic_vals) == ic_vals[-2]:
            add("interest_coverage_trend", "WATCH", "MEDIUM",
                f"Interest coverage peaked at {ic_vals[-2]:.1f}x in {ic_yrs[-2]} and declined to "
                f"{ic_vals[-1]:.1f}x in {ic_yrs[-1]}.")
 
    # ── ROE Trend (5-year) ────────────────────────────────────────────────────
    roe_5yr = [(y, all_m[y]["roe_simple"])
               for y in all_years
               if all_m[y] and all_m[y].get("roe_simple") is not None]
    if len(roe_5yr) >= 3:
        roe_vals = [v for _, v in roe_5yr]
        roe_yrs  = [y for y, _ in roe_5yr]
        if all(roe_vals[i] < roe_vals[i-1] for i in range(1, len(roe_vals))):
            add("roe_trend", "NEGATIVE", "HIGH",
                f"ROE has declined every year: "
                f"{' → '.join(f'{v:.1%}' for v in roe_vals)} ({roe_yrs[0]}–{roe_yrs[-1]}). "
                f"Structural erosion of shareholder returns.")
        elif roe_vals[-1] < roe_vals[-2] and max(roe_vals) == roe_vals[-2]:
            add("roe_trend", "WATCH", "MEDIUM",
                f"ROE peaked at {roe_vals[-2]:.1%} in {roe_yrs[-2]} and contracted to "
                f"{roe_vals[-1]:.1%} in {roe_yrs[-1]}.")
        elif all(roe_vals[i] > roe_vals[i-1] for i in range(1, len(roe_vals))):
            add("roe_trend", "POSITIVE", "LOW",
                f"ROE has improved consistently: "
                f"{' → '.join(f'{v:.1%}' for v in roe_vals)} ({roe_yrs[0]}–{roe_yrs[-1]}).")
 
    # ── Revenue CAGR (5-year) ─────────────────────────────────────────────────
    rev_5yr = [(y, normalized[y]["revenue"])
               for y in all_years
               if normalized.get(y) and normalized[y].get("revenue") is not None]
    if len(rev_5yr) >= 2:
        r_start_yr, r_start = rev_5yr[0]
        r_end_yr,   r_end   = rev_5yr[-1]
        n_years = r_end_yr - r_start_yr
        if r_start and r_start > 0 and n_years > 0:
            cagr = (r_end / r_start) ** (1 / n_years) - 1
            if cagr >= 0.05:
                add("revenue_cagr", "POSITIVE", "LOW",
                    f"Revenue CAGR of {cagr:.1%} from {r_start_yr} to {r_end_yr} "
                    f"(\\${r_start:,.0f}M → \\${r_end:,.0f}M). Solid top-line growth over the period.")
            elif cagr >= 0:
                add("revenue_cagr", "WATCH", "LOW",
                    f"Revenue CAGR of {cagr:.1%} from {r_start_yr} to {r_end_yr} "
                    f"(\\${r_start:,.0f}M → \\${r_end:,.0f}M). Modest growth — below inflation in real terms.")
            else:
                add("revenue_cagr", "NEGATIVE", "MEDIUM",
                    f"Revenue declined at a {cagr:.1%} CAGR from {r_start_yr} to {r_end_yr} "
                    f"(\\${r_start:,.0f}M → \\${r_end:,.0f}M). Top-line contraction over the full period.")
 
    # ── Liquidity Trend (5-year) ──────────────────────────────────────────────
    liq_5yr = [(y, all_m[y]["current_ratio"])
               for y in all_years
               if all_m[y] and all_m[y].get("current_ratio") is not None]
    if len(liq_5yr) >= 3:
        liq_vals = [v for _, v in liq_5yr]
        liq_yrs  = [y for y, _ in liq_5yr]
        if all(liq_vals[i] < liq_vals[i-1] for i in range(1, len(liq_vals))):
            add("liquidity_trend", "NEGATIVE", "MEDIUM",
                f"Current ratio has declined every year: "
                f"{' → '.join(f'{v:.2f}x' for v in liq_vals)} ({liq_yrs[0]}–{liq_yrs[-1]}). "
                f"Sustained deterioration in short-term liquidity.")
        elif all(liq_vals[i] > liq_vals[i-1] for i in range(1, len(liq_vals))):
            add("liquidity_trend", "POSITIVE", "LOW",
                f"Current ratio has improved consistently: "
                f"{' → '.join(f'{v:.2f}x' for v in liq_vals)} ({liq_yrs[0]}–{liq_yrs[-1]}).")
    # ── FCF Trend (5-year) ────────────────────────────────────────────────────
    fcf_5yr = [(y, all_m[y]["fcf"])
               for y in all_years
               if all_m[y] and all_m[y].get("fcf") is not None]
    if len(fcf_5yr) >= 3:
        fcf_vals = [v for _, v in fcf_5yr]
        fcf_yrs  = [y for y, _ in fcf_5yr]
        if all(fcf_vals[i] > fcf_vals[i-1] for i in range(1, len(fcf_vals))):
            add("fcf_trend", "POSITIVE", "LOW",
                f"Free cash flow has grown every year: "
                f"{' → '.join(f'\\${v:,.0f}M' for v in fcf_vals)} ({fcf_yrs[0]}–{fcf_yrs[-1]}). "
                f"Sustained FCF growth signals strong cash generation quality.")
        elif all(fcf_vals[i] < fcf_vals[i-1] for i in range(1, len(fcf_vals))):
            add("fcf_trend", "NEGATIVE", "HIGH",
                f"Free cash flow has declined every year: "
                f"{' → '.join(f'\\${v:,.0f}M' for v in fcf_vals)} ({fcf_yrs[0]}–{fcf_yrs[-1]}). "
                f"Sustained FCF deterioration undermines dividend and reinvestment capacity.")
        else:
            peak_val = max(fcf_vals)
            peak_yr  = fcf_yrs[fcf_vals.index(peak_val)]
            latest_val = fcf_vals[-1]
            latest_yr  = fcf_yrs[-1]
            if latest_val < peak_val * 0.75:
                add("fcf_trend", "WATCH", "MEDIUM",
                    f"Free cash flow peaked at ${peak_val:,.0f}M in {peak_yr} and has since fallen to "
                    f"${latest_val:,.0f}M in {latest_yr} — a {((latest_val-peak_val)/abs(peak_val)):.1%} decline from peak. "
                    f"FCF volatility warrants monitoring.")
 
    # ── Leverage Trend — Volatile / Peak Pattern ──────────────────────────────
    nd_all = [(y, all_m[y]["net_debt_to_ebitda"])
              for y in all_years
              if all_m[y] and all_m[y].get("net_debt_to_ebitda") is not None]
    if len(nd_all) >= 3:
        nd_vals = [v for _, v in nd_all]
        nd_yrs  = [y for y, _ in nd_all]
        peak_nd  = max(nd_vals)
        peak_nd_yr = nd_yrs[nd_vals.index(peak_nd)]
        latest_nd  = nd_vals[-1]
        latest_nd_yr = nd_yrs[-1]
        trough_nd = min(nd_vals)
        trough_nd_yr = nd_yrs[nd_vals.index(trough_nd)]
        swing = peak_nd - trough_nd
        if swing >= 1.0 and latest_nd > trough_nd * 1.2:
            add("leverage_trend", "WATCH", "MEDIUM",
                f"Net Debt/EBITDA has been volatile over the period: "
                f"trough of {trough_nd:.1f}x in {trough_nd_yr}, peak of {peak_nd:.1f}x in {peak_nd_yr} "
                f"(elevated by spin-off transition costs), currently {latest_nd:.1f}x in {latest_nd_yr}. "
                f"Excluding the 2019 spike, leverage has been on a structural improvement path.")
        elif swing < 0.5:
            add("leverage_trend", "POSITIVE", "LOW",
                f"Net Debt/EBITDA has remained stable across the full period "
                f"(range: {trough_nd:.1f}x – {peak_nd:.1f}x). Consistent leverage management.")
 
    # ── Dividend Sustainability (5-year) ──────────────────────────────────────
    div_5yr = []
    for y in all_years:
        n = normalized.get(y, {})
        m = all_m.get(y)
        div = n.get("dividends_paid")
        fcf_val = m.get("fcf") if m else None
        if div is not None and fcf_val is not None and fcf_val > 0:
            div_5yr.append((y, abs(div), fcf_val, abs(div) / fcf_val))
 
    if len(div_5yr) >= 3:
        ratios     = [r for _, _, _, r in div_5yr]
        div_yrs    = [y for y, _, _, _ in div_5yr]
        avg_ratio  = sum(ratios) / len(ratios)
        latest_ratio = ratios[-1]
        latest_div_yr = div_yrs[-1]
        if avg_ratio > 0.75:
            add("dividend_sustainability", "NEGATIVE", "HIGH",
                f"Dividends have consumed an average of {avg_ratio:.1%} of FCF over {len(div_5yr)} years "
                f"({div_yrs[0]}–{div_yrs[-1]}). Sustained high payout leaves minimal buffer — "
                f"any FCF compression would put the dividend at risk.")
        elif avg_ratio > 0.50:
            add("dividend_sustainability", "WATCH", "MEDIUM",
                f"Dividends have averaged {avg_ratio:.1%} of FCF over {len(div_5yr)} years "
                f"({div_yrs[0]}–{div_yrs[-1]}). Manageable but leaves limited reinvestment capacity. "
                f"Latest year payout ratio: {latest_ratio:.1%} in {latest_div_yr}.")
        else:
            add("dividend_sustainability", "POSITIVE", "LOW",
                f"Dividends have averaged {avg_ratio:.1%} of FCF over {len(div_5yr)} years "
                f"({div_yrs[0]}–{div_yrs[-1]}). Dividend is well-covered with room for reinvestment.")
    return signals
 
 
# ── STEP 5: ASSEMBLE JSON OUTPUT ──────────────────────────────────────────────
 
def build_output(normalized, metrics, signals):
    """
    Assembles the final structured JSON.
    This is what gets sent to the AI — no raw line items, only computed values.
    """
 
# ── Upgraded Trend Engine ─────────────────────────────────────────────────
    def analyze_trend(metric_name):
        """Generates a rich trend dictionary: direction, yoy_change, magnitude, consistency."""
        v20 = metrics.get(2020, {}).get(metric_name)
        v21 = metrics.get(2021, {}).get(metric_name)
        v22 = metrics.get(2022, {}).get(metric_name)
 
        if v21 is None or v22 is None:
            return {"direction": "insufficient_data", "yoy_change": None, "magnitude": None, "consistency": None}
 
        # 1. Math routing: basis points for ratios, relative % for absolute dollars
        is_ratio = "margin" in metric_name or "conversion" in metric_name or "ratio" in metric_name
        
        if is_ratio:
            delta = v22 - v21
            yoy_change = delta  
            magnitude_val = abs(delta)
            high_thresh, low_thresh = 0.05, 0.01  # 500 bps = high, 100 bps = moderate
        else:
            if v21 == 0: return {"direction": "not_meaningful", "yoy_change": None, "magnitude": None, "consistency": None}
            delta = v22 - v21
            yoy_change = delta / abs(v21)  
            magnitude_val = abs(yoy_change)
            high_thresh, low_thresh = 0.20, 0.05  # 20% = high, 5% = moderate
 
        # 2. Direction
        # Materiality threshold: 10 bps for margins, $1M for absolute dollars
        threshold = 0.001 if is_ratio else 1.0 
        
        if delta > threshold: 
            direction = "improving"
        elif delta < -threshold: 
            direction = "deteriorating"
        else: 
            direction = "stable"
 
        # 3. Magnitude
        if magnitude_val > high_thresh: magnitude = "high"
        elif magnitude_val > low_thresh: magnitude = "moderate"
        else: magnitude = "low"
 
        # 4. Consistency
        consistency = "insufficient_data"
        if v20 is not None:
            delta_prev = v21 - v20
            if direction == "stable":
                consistency = "stable"
            elif (delta > 0 and delta_prev > 0) or (delta < 0 and delta_prev < 0):
                consistency = "consistent"
            else:
                consistency = "volatile"
 
        return {
            "direction": direction,
            "yoy_change": round(yoy_change, 4),
            "magnitude": magnitude,
            "consistency": consistency
        }
 
    # ── Assemble Output ───────────────────────────────────────────────────────
    output = {
        "company": "Dow Inc.",
        "ticker": "DOW",
        "fiscal_years_analyzed": YEARS,
        "currency": "USD millions",
        "data_source": "SEC 10-K 2023 Filing",
 
        "metrics_by_year": {
            str(year): metrics[year] for year in YEARS if year in metrics
        },
 
        "trends": {
            "core_operating_margin":  analyze_trend("core_operating_margin"),
            "gross_margin":           analyze_trend("gross_margin"),
            "net_margin":             analyze_trend("net_margin"),
            "fcf_conversion":         analyze_trend("fcf_conversion"),
            "revenue":                analyze_trend("revenue"),
            "ebitda_margin":          analyze_trend("ebitda_margin"),
        },
 
        "signals": signals,
 
        "signal_summary": {
            "total":    len(signals),
            "negative": len([s for s in signals if s["signal"] == "NEGATIVE"]),
            "watch":    len([s for s in signals if s["signal"] == "WATCH"]),
            "positive": len([s for s in signals if s["signal"] == "POSITIVE"]),
            "high_severity": len([s for s in signals if s["severity"] == "HIGH"]),
        }
    }
 
    return output   
 
 
# ── MAIN ──────────────────────────────────────────────────────────────────────
 
def run():
    print("Loading statements...")
    income, balance, cashflow = load_all_statements()
 
    print("Normalizing data...")
    normalized = normalize(income, balance, cashflow)
 
    print("Calculating metrics...")
    metrics = calculate_metrics(normalized)
 
    print("Generating signals...")
    signals = generate_signals(metrics, normalized)
 
    print("Assembling output...\n")
    output = build_output(normalized, metrics, signals)
 
    # Print clean JSON
    print(json.dumps(output, indent=2, default=str))
 
    # Also save to file
    with open("output.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
 
    print("\n✅ output.json saved.")
    return output
 
 
if __name__ == "__main__":
    run()