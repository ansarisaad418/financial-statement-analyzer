"""
Financial Statement Analyzer — AI Interpretation Layer
Reads output.json produced by engine.py and sends it to Gemini for analyst commentary.

Rules:
  - AI receives ONLY pre-computed metrics and signals. No raw numbers.
  - AI must NEVER invent figures or recalculate ratios.
  - AI must NEVER contradict the mathematical signals.
  - Output is concise, active-voice, analyst-style commentary.
"""

import json
import os
from google import genai

# ── CONFIG ────────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("GEMINI_API_KEY") or open("secrets.txt").read().strip()

INPUT_FILE = "output.json"

# ── LOAD COMPUTED DATA ────────────────────────────────────────────────────────

def load_analysis():
    with open(INPUT_FILE, "r") as f:
        return json.load(f)


# ── BUILD PROMPT ──────────────────────────────────────────────────────────────

def build_prompt(data):
    company  = data["company"]
    ticker   = data["ticker"]
    years    = data["fiscal_years_analyzed"]
    currency = data["currency"]
    metrics  = data["metrics_by_year"]
    trends   = data["trends"]
    signals  = data["signals"]
    summary  = data["signal_summary"]

    metrics_block = ""
    for year in years:
        m = metrics.get(str(year), {})
        metrics_block += f"\n  {year}:\n"
        for k, v in m.items():
            if v is not None:
                if "margin" in k or "conversion" in k or "burden" in k or "roe" in k:
                    metrics_block += f"    {k}: {v:.1%}\n"
                elif "ratio" in k or "coverage" in k or "turnover" in k or "factor" in k or "ebitda" in k.lower():
                    metrics_block += f"    {k}: {v:.2f}x\n"
                else:
                    metrics_block += f"    {k}: {v}\n"

    trends_block = ""
    for metric, direction in trends.items():
        trends_block += f"  {metric}: {direction['2020_to_2021']} (2020→2021), {direction['2021_to_2022']} (2021→2022)\n"

    signals_block = ""
    for s in signals:
        signals_block += f"  [{s['signal']}][{s['severity']}] {s['metric']}: {s['finding']}\n"

    prompt = f"""
You are a senior equity research analyst writing a structured company analysis.

STRICT RULES — you must follow these without exception:
1. Use ONLY the pre-computed metrics and signals provided below. Do NOT perform any calculations.
2. Do NOT invent, estimate, or reference any numbers not explicitly provided.
3. Do NOT contradict any signal. If a signal says deteriorating, your commentary must reflect that.
4. Write in active voice. Be direct and concise. No filler phrases like "it is worth noting."
5. Structure your output exactly as specified below.
6. All figures you mention must come directly from the metrics provided.

COMPANY: {company} ({ticker})
FISCAL YEARS ANALYZED: {', '.join(str(y) for y in years)}
CURRENCY: {currency}

PRE-COMPUTED METRICS:
{metrics_block}

TREND DIRECTIONS:
{trends_block}

RULE-BASED SIGNALS ({summary['total']} total — {summary['positive']} positive, {summary['watch']} watch, {summary['negative']} negative):
{signals_block}

OUTPUT STRUCTURE — write exactly these five sections:

1. EXECUTIVE SUMMARY (3 sentences max)
   The single most important takeaway about this company's financial health.
   Lead with the dominant narrative from the signals, not a balanced summary.

2. PROFITABILITY
   Analyze margin trajectory across the 3 years. Distinguish core operating performance
   from reported figures. Call out any non-core income dependency explicitly.

3. CASH GENERATION & EARNINGS QUALITY
   Assess FCF conversion and what it tells us about the reliability of reported earnings.
   Note any divergence between accounting profit and cash generation.

4. BALANCE SHEET & LEVERAGE
   Assess the debt load, liquidity position, and interest coverage.
   Comment on whether the balance sheet provides a buffer or creates risk.

5. KEY RISKS TO MONITOR
   List the top 3 risks flagged by the signal engine, ranked by severity.
   Each risk must directly reference a specific signal finding.

Do not add any sections beyond these five.
Do not use bullet points inside sections — write in prose.
"""

    return prompt


# ── CALL GEMINI ───────────────────────────────────────────────────────────────

def get_commentary(prompt):
    client = genai.Client(api_key=API_KEY)

    fallback_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

    for model_name in fallback_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text, model_name
        except Exception as e:
            print(f"  {model_name} failed: {e}")
            continue

    return None, None


# ── VALIDATE OUTPUT ───────────────────────────────────────────────────────────

def validate(commentary, signals):
    issues = []

    contradiction_map = {
        "core_operating_margin": ["margin expanded", "margin improving", "margins grew"],
        "fcf_conversion":        ["weak cash", "poor conversion"],
        "net_debt_to_ebitda":    ["dangerously leveraged", "debt crisis"],
        "interest_coverage":     ["cannot cover interest", "interest risk"],
    }

    for signal in signals:
        if signal["signal"] == "NEGATIVE":
            metric = signal["metric"]
            if metric in contradiction_map:
                for phrase in contradiction_map[metric]:
                    if phrase.lower() in commentary.lower():
                        issues.append(f"Possible contradiction: AI used '{phrase}' but signal for {metric} is NEGATIVE.")

    return issues


# ── SAVE OUTPUT ───────────────────────────────────────────────────────────────

def save_commentary(commentary, model_used):
    output = {
        "model_used": model_used,
        "commentary": commentary
    }
    with open("commentary.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n✅ commentary.json saved.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run():
    print("Loading analysis data...")
    data = load_analysis()

    print("Building prompt...")
    prompt = build_prompt(data)

    print("Calling Gemini API...")
    commentary, model_used = get_commentary(prompt)

    if not commentary:
        print("❌ All Gemini models failed. Check your API key.")
        return

    print(f"\nModel used: {model_used}")
    print("\n" + "="*80)
    print("ANALYST COMMENTARY")
    print("="*80)
    print(commentary)

    print("\nValidating output...")
    issues = validate(commentary, data["signals"])
    if issues:
        print("\n⚠️  VALIDATION WARNINGS:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ No contradictions detected.")

    save_commentary(commentary, model_used)


if __name__ == "__main__":
    run()
