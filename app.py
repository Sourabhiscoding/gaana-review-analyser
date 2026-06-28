import streamlit as st
import anthropic
import pandas as pd
import json
import io

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gaana Review Analyser",
    page_icon="🎵",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0D0D0D; }

.hero {
    background: linear-gradient(135deg, #1a0533 0%, #0D0D0D 60%);
    border: 1px solid #2a1040;
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
}
.hero h1 { font-size: 2rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem; }
.hero p  { color: #888; font-size: 0.95rem; margin: 0; }
.hero span { color: #C850C0; }

.card {
    background: #141414;
    border: 1px solid #222;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.card h3 { color: #fff; font-size: 1rem; font-weight: 600; margin: 0 0 0.75rem; }

.theme-block {
    background: #1a1a1a;
    border-left: 3px solid #C850C0;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.theme-block .theme-name { color: #C850C0; font-weight: 600; font-size: 0.9rem; }
.theme-block .theme-body { color: #ccc; font-size: 0.85rem; margin-top: 0.4rem; line-height: 1.6; }

.quote-chip {
    background: #1f1f1f;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    color: #aaa;
    font-size: 0.82rem;
    font-style: italic;
    margin-bottom: 0.5rem;
}

.stat-pill {
    display: inline-block;
    background: #2a0f3a;
    color: #C850C0;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 0.5rem;
}

.segment-tag {
    display: inline-block;
    background: #0f2a1a;
    color: #4ade80;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 0.2rem 0.2rem 0.2rem 0;
}

.unmet-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid #222;
    color: #ccc;
    font-size: 0.87rem;
}
.unmet-item:last-child { border-bottom: none; }

hr { border-color: #222; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎵 Gaana <span>Review Analyser</span></h1>
  <p>AI-powered discovery failure analysis · Paste reviews or upload a CSV · Get PM-ready insights instantly</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: API Key ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Anthropic API Key", type="password",
                            help="Get yours at console.anthropic.com")
    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown("""
1. Paste reviews or upload CSV
2. Click Analyse
3. Claude identifies discovery pain themes
4. Export insights for your deck
    """)
    st.markdown("---")
    st.caption("Built for Gaana PM Graduation Project · Jun 2026")

# ── Input section ─────────────────────────────────────────────
st.markdown("### 📥 Input Reviews")

tab1, tab2 = st.tabs(["📋 Paste Reviews", "📂 Upload CSV"])

reviews_text = ""

with tab1:
    pasted = st.text_area(
        "Paste reviews here (one per line, or comma-separated):",
        height=200,
        placeholder="The recommendation algorithm is terrible...\nSame 10 songs keep repeating...\nI can't discover new music..."
    )
    if pasted:
        reviews_text = pasted

with tab2:
    uploaded = st.file_uploader("Upload CSV with a 'review' column", type=["csv"])
    if uploaded:
        df_up = pd.read_csv(uploaded)
        if 'review' in df_up.columns:
            reviews_text = "\n".join(df_up['review'].dropna().astype(str).tolist())
            st.success(f"✅ Loaded {len(df_up)} reviews from CSV")
            with st.expander("Preview"):
                st.dataframe(df_up[['review']].head(10))
        else:
            st.error("CSV must have a 'review' column")

# ── Analyse button ────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    analyse_btn = st.button("🔍 Analyse Reviews", type="primary", use_container_width=True)

# ── Analysis logic ────────────────────────────────────────────
if analyse_btn:
    if not api_key:
        st.error("⚠️ Please enter your Anthropic API key in the sidebar.")
    elif not reviews_text.strip():
        st.error("⚠️ Please paste some reviews or upload a CSV first.")
    else:
        with st.spinner("Claude is analysing discovery patterns..."):

            SYSTEM_PROMPT = """You are a senior product analyst specialising in music streaming apps.
Your task: analyse user reviews of Gaana (Indian music streaming app) and extract actionable PM insights focused on music discovery failures.

You must respond with ONLY valid JSON, no preamble, no markdown fences.

Return this exact structure:
{
  "total_reviews_analysed": <integer>,
  "discovery_related_count": <integer>,
  "overall_sentiment": "<Mostly Negative | Mixed | Mostly Positive>",
  "top_themes": [
    {
      "theme_name": "<short name>",
      "frequency_pct": <integer 0-100>,
      "severity": "<High | Medium | Low>",
      "description": "<2 sentences explaining the theme>",
      "sample_quotes": ["<quote1>", "<quote2>"]
    }
  ],
  "user_segments": [
    {
      "segment_name": "<name>",
      "description": "<1 sentence>",
      "primary_pain": "<their main complaint>"
    }
  ],
  "unmet_needs": ["<need 1>", "<need 2>", "<need 3>", "<need 4>", "<need 5>"],
  "biggest_opportunity": "<2-3 sentence PM insight on the single biggest opportunity>",
  "ai_advantage": "<Why AI specifically solves this better than rule-based systems — 2 sentences>"
}"""

            USER_PROMPT = f"""Analyse these Gaana user reviews and return the JSON insight report:

REVIEWS:
{reviews_text[:8000]}"""

            try:
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": USER_PROMPT}]
                )

                raw = message.content[0].text.strip()
                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw)

                # ── Results ───────────────────────────────────────
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")

                # Summary pills
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Reviews Analysed", data.get("total_reviews_analysed", "—"))
                col_b.metric("Discovery-Related", data.get("discovery_related_count", "—"))
                col_c.metric("Overall Sentiment", data.get("overall_sentiment", "—"))
                col_d.metric("Themes Found", len(data.get("top_themes", [])))

                st.markdown("---")

                # Top themes
                st.markdown("### 🔥 Top Discovery Pain Themes")
                for theme in data.get("top_themes", []):
                    sev_color = {"High": "#ff4444", "Medium": "#ffaa00", "Low": "#44ff88"}.get(theme.get("severity"), "#888")
                    quotes_html = "".join([f'<div class="quote-chip">"{q}"</div>' for q in theme.get("sample_quotes", [])])
                    st.markdown(f"""
<div class="theme-block">
  <div class="theme-name">{theme['theme_name']}
    <span style="color:{sev_color};font-size:0.75rem;margin-left:0.5rem;">● {theme.get('severity','?')} severity</span>
    <span style="color:#888;font-size:0.75rem;margin-left:0.5rem;">{theme.get('frequency_pct','?')}% of reviews</span>
  </div>
  <div class="theme-body">{theme.get('description','')}</div>
  <div style="margin-top:0.75rem">{quotes_html}</div>
</div>
""", unsafe_allow_html=True)

                # User segments + Unmet needs side by side
                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("### 👥 User Segments")
                    for seg in data.get("user_segments", []):
                        st.markdown(f"""
<div class="card">
  <h3>{seg.get('segment_name','')}</h3>
  <p style="color:#aaa;font-size:0.85rem;margin:0 0 0.5rem">{seg.get('description','')}</p>
  <p style="color:#C850C0;font-size:0.82rem;margin:0">⚡ {seg.get('primary_pain','')}</p>
</div>
""", unsafe_allow_html=True)

                with col_right:
                    st.markdown("### 💡 Unmet Needs")
                    needs_html = "".join([f'<div class="unmet-item">→ {n}</div>' for n in data.get("unmet_needs", [])])
                    st.markdown(f'<div class="card">{needs_html}</div>', unsafe_allow_html=True)

                # Biggest opportunity
                st.markdown("### 🎯 Biggest PM Opportunity")
                st.markdown(f"""
<div class="card" style="border-color:#2a1040;">
  <p style="color:#C850C0;font-size:0.9rem;line-height:1.7;margin:0">{data.get('biggest_opportunity','')}</p>
</div>
""", unsafe_allow_html=True)

                # AI advantage
                st.markdown("### 🤖 Why AI (not rule-based systems)")
                st.markdown(f"""
<div class="card" style="border-color:#0f2a1a;">
  <p style="color:#4ade80;font-size:0.9rem;line-height:1.7;margin:0">{data.get('ai_advantage','')}</p>
</div>
""", unsafe_allow_html=True)

                # Export
                st.markdown("---")
                st.markdown("### 📤 Export")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.download_button(
                        "⬇️ Download JSON Report",
                        data=json.dumps(data, indent=2),
                        file_name="gaana_review_insights.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with col_e2:
                    # Flatten for CSV
                    flat = {
                        "total_reviews": data.get("total_reviews_analysed"),
                        "discovery_related": data.get("discovery_related_count"),
                        "sentiment": data.get("overall_sentiment"),
                        "biggest_opportunity": data.get("biggest_opportunity"),
                        "ai_advantage": data.get("ai_advantage"),
                    }
                    st.download_button(
                        "⬇️ Download Summary CSV",
                        data=pd.DataFrame([flat]).to_csv(index=False),
                        file_name="gaana_summary.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

            except json.JSONDecodeError as e:
                st.error(f"JSON parse error: {e}\n\nRaw response:\n{raw}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
