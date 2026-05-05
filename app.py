"""
Financial Statement Analyzer — Streamlit Frontend
Financial Analysis Dashboard

Pipeline:
  1. User uploads Excel file
  2. engine.py runs automatically → produces metrics + signals
  3. User clicks "Generate Commentary" → interpreter.py calls Gemini
  4. Full analyst report displayed with charts
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import tempfile

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial Statement Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── IMPORT ENGINE & INTERPRETER ───────────────────────────────────────────────

from engine import load_all_statements, normalize, calculate_metrics, generate_signals, build_output
from interpreter import build_prompt, get_commentary, validate

# ── API KEY — read from Streamlit secrets, fall back to sidebar input ─────────

try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    api_key = ""

# ── SESSION STATE ─────────────────────────────────────────────────────────────

if "output" not in st.session_state:
    st.session_state.output = None
if "commentary" not in st.session_state:
    st.session_state.commentary = None
if "model_used" not in st.session_state:
    st.session_state.model_used = None

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Settings")

    if not api_key:
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Your Gemini API key from Google AI Studio"
        )

    st.divider()
    st.markdown("### 📁 About")
    st.info(
        "This system reads audited financial statements, "
        "computes deterministic metrics and signals, "
        "then uses AI strictly for interpretation — "
        "never for calculation."
    )

    st.divider()
    if st.button("🔄 Reset Analysis"):
        st.session_state.output = None
        st.session_state.commentary = None
        st.session_state.model_used = None
        st.rerun()

# ── HEADER ────────────────────────────────────────────────────────────────────

st.title("📊 Financial Statement Analyzer")
st.caption("Deterministic signal engine + controlled AI interpretation")

st.divider()

# ── FILE UPLOAD ───────────────────────────────────────────────────────────────

st.markdown("### 📂 Upload Financial Statements")
uploaded_file = st.file_uploader(
    "Upload your Excel file (Income Statement, Balance Sheet, Cash Flow — 3 sheets)",
    type=["xlsx"]
)

if uploaded_file is not None and st.session_state.output is None:
    with st.spinner("Running engine — computing metrics and signals..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            import engine as eng
            eng.FILE_PATH = tmp_path

            income, balance, cashflow = load_all_statements()
            normalized = normalize(income, balance, cashflow)
            metrics = calculate_metrics(normalized)
            signals = generate_signals(metrics, normalized)
            output = build_output(normalized, metrics, signals)

            st.session_state.output = output
            st.success("✅ Engine complete — metrics and signals computed.")

        except Exception as e:
            st.error(f"❌ Engine error: {e}")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

if st.session_state.output is not None:
    output = st.session_state.output
    metrics = output["metrics_by_year"]
    signals = output["signals"]
    summary = output["signal_summary"]
    years = [str(y) for y in output["fiscal_years_analyzed"]]

    st.divider()

    # ── SIGNAL SUMMARY BANNER ─────────────────────────────────────────────────
    st.markdown("### 🚦 Signal Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Signals", summary["total"])
    col2.metric("🔴 Negative", summary["negative"])
    col3.metric("🟡 Watch", summary["watch"])
    col4.metric("🟢 Positive", summary["positive"])

    st.divider()

    # ── KEY METRICS TABLE ─────────────────────────────────────────────────────
    st.markdown("### 📐 Key Metrics by Year")

    metric_rows = {
        "Gross Margin":           ("gross_margin", "pct"),
        "Core Operating Margin":  ("core_operating_margin", "pct"),
        "EBITDA Margin":          ("ebitda_margin", "pct"),
        "Net Margin":             ("net_margin", "pct"),
        "FCF Conversion":         ("fcf_conversion", "pct"),
        "CFO Conversion":         ("cfo_conversion", "pct"),
        "Current Ratio":          ("current_ratio", "x"),
        "Quick Ratio":            ("quick_ratio", "x"),
        "Net Debt / EBITDA":      ("net_debt_to_ebitda", "x"),
        "Interest Coverage":      ("interest_coverage", "x"),
        "Asset Turnover":         ("asset_turnover", "x"),
        "ROE (Simple)":           ("roe_simple", "pct"),
    }

    table_data = {}
    for label, (key, fmt) in metric_rows.items():
        row = []
        for y in years:
            val = metrics.get(y, {}).get(key)
            if val is None:
                row.append("—")
            elif fmt == "pct":
                row.append(f"{val:.1%}")
            else:
                row.append(f"{val:.2f}x")
        table_data[label] = row

    df_metrics = pd.DataFrame(table_data, index=years).T
    st.dataframe(df_metrics, use_container_width=True)

    st.divider()

    # ── CHARTS ────────────────────────────────────────────────────────────────
    st.markdown("### 📈 Visual Analysis")

    def get_pct(key):
        return [(metrics.get(y, {}).get(key) or 0) * 100 for y in years]

    def get_val(key):
        return [metrics.get(y, {}).get(key) or 0 for y in years]

    years_int = [int(y) for y in years]

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("#### Margin Trend")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=years_int, y=get_pct("gross_margin"),
            mode="lines+markers", name="Gross Margin",
            line=dict(color="#2196F3", width=2.5), marker=dict(size=8)))
        fig1.add_trace(go.Scatter(x=years_int, y=get_pct("core_operating_margin"),
            mode="lines+markers", name="Core Op. Margin",
            line=dict(color="#FF9800", width=2.5), marker=dict(size=8)))
        fig1.add_trace(go.Scatter(x=years_int, y=get_pct("ebitda_margin"),
            mode="lines+markers", name="EBITDA Margin",
            line=dict(color="#4CAF50", width=2.5), marker=dict(size=8)))
        fig1.add_trace(go.Scatter(x=years_int, y=get_pct("net_margin"),
            mode="lines+markers", name="Net Margin",
            line=dict(color="#9C27B0", width=2.5), marker=dict(size=8)))
        fig1.update_layout(
            yaxis_title="Margin (%)", xaxis_title="Year",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with chart2:
        st.markdown("#### Earnings Quality (FCF & CFO Conversion)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=years_int, y=get_pct("fcf_conversion"),
            name="FCF Conversion", marker_color="#2196F3", opacity=0.85))
        fig2.add_trace(go.Bar(x=years_int, y=get_pct("cfo_conversion"),
            name="CFO Conversion", marker_color="#4CAF50", opacity=0.85))
        fig2.add_hline(y=100, line_dash="dash", line_color="red",
            annotation_text="100% threshold", annotation_position="right")
        fig2.update_layout(
            yaxis_title="Conversion (%)", xaxis_title="Year",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        st.plotly_chart(fig2, use_container_width=True)

    chart3, chart4 = st.columns(2)

    with chart3:
        st.markdown("#### Leverage & Coverage")
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(go.Bar(
            x=years_int, y=get_val("net_debt_to_ebitda"),
            name="Net Debt/EBITDA", marker_color="#FF5722", opacity=0.8),
            secondary_y=False)
        fig3.add_trace(go.Scatter(
            x=years_int, y=get_val("interest_coverage"),
            mode="lines+markers", name="Interest Coverage",
            line=dict(color="#2196F3", width=2.5), marker=dict(size=8)),
            secondary_y=True)
        fig3.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        fig3.update_yaxes(title_text="Net Debt/EBITDA (x)", secondary_y=False)
        fig3.update_yaxes(title_text="Interest Coverage (x)", secondary_y=True)
        st.plotly_chart(fig3, use_container_width=True)

    with chart4:
        st.markdown("#### Liquidity Ratios")
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=years_int, y=get_val("current_ratio"),
            name="Current Ratio", marker_color="#4CAF50", opacity=0.85))
        fig4.add_trace(go.Bar(x=years_int, y=get_val("quick_ratio"),
            name="Quick Ratio", marker_color="#FF9800", opacity=0.85))
        fig4.add_hline(y=1.0, line_dash="dash", line_color="red",
            annotation_text="1.0x minimum", annotation_position="right")
        fig4.update_layout(
            yaxis_title="Ratio (x)", xaxis_title="Year",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        st.plotly_chart(fig4, use_container_width=True)

    chart5, chart6 = st.columns(2)

    with chart5:
        st.markdown("#### DuPont ROE Decomposition")
        dupont_metrics = {
            "Tax Burden":      "dupont_tax_burden",
            "Interest Burden": "dupont_interest_burden",
            "Leverage Factor": "dupont_leverage_factor",
        }
        fig5 = go.Figure()
        colors = ["#2196F3", "#FF9800", "#4CAF50"]
        for (label, key), color in zip(dupont_metrics.items(), colors):
            fig5.add_trace(go.Scatter(
                x=years_int, y=get_val(key),
                mode="lines+markers", name=label,
                line=dict(color=color, width=2.5), marker=dict(size=8)))
        fig5.update_layout(
            yaxis_title="Factor Value", xaxis_title="Year",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        st.plotly_chart(fig5, use_container_width=True)

    with chart6:
        st.markdown("#### Capital Allocation vs FCF")
        fcf_vals = [abs(v) for v in get_val("fcf")]
        cash_ret = get_val("total_cash_returned")
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(x=years_int, y=fcf_vals,
            name="Free Cash Flow", marker_color="#4CAF50", opacity=0.85))
        fig6.add_trace(go.Bar(x=years_int, y=cash_ret,
            name="Cash Returned to Shareholders", marker_color="#FF5722", opacity=0.85))
        fig6.update_layout(
            yaxis_title="USD Millions", xaxis_title="Year",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=40, b=20), height=350,
            xaxis=dict(tickvals=years_int, ticktext=years)
        )
        st.plotly_chart(fig6, use_container_width=True)

    st.divider()

    # ── SIGNALS PANEL ─────────────────────────────────────────────────────────
    st.markdown("### 🚨 Detected Signals")

    severity_colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    signal_colors   = {"NEGATIVE": "error", "WATCH": "warning", "POSITIVE": "success"}
    severity_order  = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_signals  = sorted(signals, key=lambda s: severity_order.get(s["severity"], 3))

    for s in sorted_signals:
        icon     = severity_colors.get(s["severity"], "⚪")
        box_type = signal_colors.get(s["signal"], "info")
        label    = f"{icon} **{s['metric'].replace('_', ' ').title()}** — [{s['signal']}][{s['severity']}]"

        if box_type == "error":
            st.error(f"{label}\n\n{s['finding']}")
        elif box_type == "warning":
            st.warning(f"{label}\n\n{s['finding']}")
        else:
            st.success(f"{label}\n\n{s['finding']}")

    st.divider()

    # ── GENERATE COMMENTARY ───────────────────────────────────────────────────
    st.markdown("### 🤖 AI Analyst Commentary")
    st.caption("AI receives only pre-computed signals — it never sees raw numbers or performs calculations.")

    if st.button("📝 Generate Analyst Commentary", type="primary", use_container_width=True):
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar.")
        else:
            with st.spinner("Calling Gemini — generating analyst commentary..."):
                try:
                    import interpreter as interp
                    interp.API_KEY = api_key

                    prompt = build_prompt(output)
                    commentary, model_used = get_commentary(prompt)

                    if commentary:
                        st.session_state.commentary = commentary
                        st.session_state.model_used = model_used
                    else:
                        st.error("❌ All Gemini models failed. Check your API key.")
                except Exception as e:
                    st.error(f"❌ Interpreter error: {e}")

    # ── DISPLAY COMMENTARY ────────────────────────────────────────────────────
    if st.session_state.commentary:
        commentary = st.session_state.commentary

        st.caption(f"Model: {st.session_state.model_used}")

        issues = validate(commentary, signals)
        if issues:
            st.warning("⚠️ Validation warnings detected:")
            for issue in issues:
                st.caption(f"— {issue}")

        sections = [
            "1. EXECUTIVE SUMMARY",
            "2. PROFITABILITY",
            "3. CASH GENERATION & EARNINGS QUALITY",
            "4. BALANCE SHEET & LEVERAGE",
            "5. KEY RISKS TO MONITOR",
        ]
        section_icons = ["📌", "💰", "💵", "🏦", "⚠️"]

        for i, (section, icon) in enumerate(zip(sections, section_icons)):
            start = commentary.find(section)
            if start == -1:
                continue
            next_starts = [commentary.find(s) for s in sections[i+1:] if commentary.find(s) != -1]
            end = min(next_starts) if next_starts else len(commentary)
            body = commentary[start:end].strip()[len(section):].strip()

            with st.expander(f"{icon} {section}", expanded=True):
                st.markdown(body)

        st.divider()
        st.download_button(
            label="⬇️ Download Full Commentary",
            data=commentary,
            file_name="analyst_commentary.txt",
            mime="text/plain",
            use_container_width=True
        )
