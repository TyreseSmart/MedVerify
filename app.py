"""
app.py
"""

import streamlit as st
from medgemma_analyzer import analyze_health_claim_stream, parse_model_output
from pubmed_search import get_evidence_for_claim

# Page config
st.set_page_config(
    page_title="MedVerify",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global CSS
st.markdown("""
<style>
body, .stMarkdown {
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
}

/* Score ring gauge */
.score-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 0 8px;
}
.score-ring {
    position: relative;
    width: 140px;
    height: 140px;
}
.score-ring svg { transform: rotate(-90deg); }
.score-ring-number {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    line-height: 1.1;
}
.score-val   { font-size: 2.4rem; font-weight: 800; display: block; }
.score-total { font-size: 0.85rem; color: #94a3b8; }
.score-label { margin-top: 8px; font-size: 0.88rem; color: #64748b; font-weight: 500; }

/* Risk badges */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88rem;
    margin: 3px 3px 3px 0;
}
.badge-safe    { background:#d1fae5; color:#065f46; }
.badge-mislead { background:#fef3c7; color:#92400e; }
.badge-danger  { background:#fee2e2; color:#991b1b; }
.badge-high    { background:#ef4444; color:#fff; }
.badge-medium  { background:#f59e0b; color:#fff; }
.badge-low     { background:#10b981; color:#fff; }
.badge-source  { background:#e0f2fe; color:#0369a1; font-size:0.76rem; padding:3px 9px; }
.badge-strong  { background:#d1fae5; color:#065f46; font-size:0.78rem; padding:3px 9px; }
.badge-journal { background:#dbeafe; color:#1d4ed8; font-size:0.78rem; padding:3px 9px; }

/* Generic cards */
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 12px;
}

/* Analysis summary card */
.summary-card {
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    border-radius: 0 10px 10px 0;
    padding: 16px 20px;
    line-height: 1.8;
    color: #334155;
    margin-bottom: 12px;
}

/* Logical fallacy card */
.fallacy-card {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 10px;
}
.fallacy-name { font-weight: 700; color: #b45309; margin-bottom: 6px; }
.fallacy-desc { color: #78350f; font-size: 0.9rem; line-height: 1.65; }

/* Evidence source card */
.evidence-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.evidence-title  { font-weight: 700; color: #1e293b; font-size: 0.95rem; margin-bottom: 4px; }
.evidence-meta   { color: #64748b; font-size: 0.82rem; margin-bottom: 10px; }
.evidence-text   { color: #475569; font-size: 0.88rem; line-height: 1.65; }

/* Risk cards */
.risk-card         { background:#fff5f5; border:1px solid #fecaca; border-radius:12px; padding:20px 22px; line-height:1.8; color:#7f1d1d; font-size:0.95rem; }
.risk-card-mislead { background:#fffbeb; border:1px solid #fde68a; color:#78350f; border-radius:12px; padding:20px 22px; line-height:1.8; font-size:0.95rem; }
.risk-card-safe    { background:#f0fdf4; border:1px solid #bbf7d0; color:#14532d;  border-radius:12px; padding:20px 22px; line-height:1.8; font-size:0.95rem; }

/* Scientific rebuttal */
.rebuttal-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 22px;
    line-height: 1.85;
    color: #334155;
    font-size: 0.95rem;
    margin-bottom: 14px;
}
.social-card {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 16px 20px;
    color: #166534;
    font-size: 0.92rem;
    line-height: 1.75;
    margin-bottom: 12px;
}
.social-label {
    font-weight: 700;
    font-size: 0.88rem;
    color: #15803d;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

footer { visibility: hidden; }

/* Tab tweaks */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { padding: 8px 18px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# Helper: circular score SVG
def score_ring_html(score: int) -> str:
    r       = 54
    circum  = 2 * 3.14159 * r
    done    = circum * score / 100
    rest    = circum - done
    color   = "#10b981" if score >= 70 else ("#f59e0b" if score >= 40 else "#ef4444")
    conf    = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
    return f"""
<div class="score-ring-wrap">
  <div class="score-ring">
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r="{r}" fill="none" stroke="#f1f5f9" stroke-width="12"/>
      <circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="12"
        stroke-linecap="round" stroke-dasharray="{done:.1f} {rest:.1f}"/>
    </svg>
    <div class="score-ring-number">
      <span class="score-val" style="color:{color}">{score}</span>
      <span class="score-total">/ 100</span>
    </div>
  </div>
  <div class="score-label">Credibility Score · Confidence: {conf}</div>
</div>"""


# Helper: risk badges
def risk_badges_html(risk_level: str) -> str:
    main = {"Safe":("badge-safe","✅ Safe"), "Misleading":("badge-mislead","⚠️ Misleading"), "Dangerous":("badge-danger","🚨 Dangerous")}
    sub  = {"Safe":("badge-low","Low risk"), "Misleading":("badge-medium","Medium risk"), "Dangerous":("badge-high","High risk")}
    mc, ml = main.get(risk_level, ("badge-mislead","⚠️ Misleading"))
    sc, sl = sub.get(risk_level,  ("badge-medium","Medium risk"))
    return f'<span class="badge {mc}">{ml}</span><span class="badge {sc}">{sl}</span>'


# Sidebar
with st.sidebar:
    st.markdown("## 🩺 MedVerify")
    st.caption("AI-powered medical misinformation detection")
    st.divider()
    st.markdown("### About the model")
    st.markdown(
        "This system uses **Google MedGemma 1.5-4B-IT**, "
        "a multimodal LLM trained for medical domain by Google."
    )
    st.markdown("[MedGemma paper](https://arxiv.org/abs/2507.05201)")
    st.divider()
    enable_pubmed = st.toggle("Search PubMed literature", value=True)
    st.divider()
    st.caption("For reference only; not a substitute for professional medical advice.")


# Main UI
st.title("MedVerify")
st.markdown(
    "Identify **medical misinformation** and **misleading health claims** on social media, "
    "and protect yourself and your family from false medical information."
)
st.divider()

st.markdown("## Enter health claim to verify")

user_input = st.text_area(
    label="Health claim",
    value=st.session_state.get("input_text", ""),
    height=140,
    placeholder="e.g.: Drinking alkaline water daily can prevent cancer…",
    label_visibility="collapsed",
)
char_count = len(user_input)
st.caption(f"{char_count} / 5000 characters")

col_btn, col_clear, _ = st.columns([1.2, 0.8, 5])
with col_btn:
    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear", use_container_width=True):
        st.session_state["input_text"] = ""
        st.rerun()


# Run analysis
if analyze_btn:
    if not user_input.strip():
        st.warning("Please enter a health claim first.")
        st.stop()


    st.divider()

    # Stream output
    with st.expander("🤖 View model generation in real time", expanded=True):
        st.caption("MedGemma is analyzing; content is being generated…")
        try:
            raw_text = st.write_stream(analyze_health_claim_stream(user_input))
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    result = parse_model_output(raw_text)

    # PubMed search
    pubmed_papers = []
    if enable_pubmed:
        with st.spinner("Searching PubMed for relevant literature…"):
            try:
                pubmed_papers = get_evidence_for_claim(user_input)
            except Exception:
                pubmed_papers = []

    # Get result data
    score       = result.get("credibility_score", 50)
    risk_level  = result.get("risk_level", "Misleading")
    risk_reason = result.get("risk_reason", "")
    medical_acc = result.get("medical_accuracy", "")
    fallacies   = result.get("logical_fallacies", [])
    misconceptions = result.get("key_misconceptions", [])
    evidence_sum= result.get("evidence_summary", "")
    rebuttal    = result.get("rebuttal", "")
    recommend   = result.get("recommendation", "")

    # Summary row
    st.markdown("## Analysis Report")
    col_score, col_summary = st.columns([1, 3])

    with col_score:
        st.markdown(score_ring_html(score), unsafe_allow_html=True)

    with col_summary:
        st.markdown("#### 🛡️ Analysis Summary")
        st.markdown(
            f'<div class="summary-card">{medical_acc}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(risk_badges_html(risk_level), unsafe_allow_html=True)
        if risk_reason:
            st.caption(risk_reason)

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Score Basis",
        "Evidence",
        "Risk Assessment",
        "Scientific Rebuttal",
    ])

    # Tab 1: Score Basis
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)

        # Medical accuracy
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">Medical Accuracy Assessment</div>'
            f'<div style="color:#475569;line-height:1.8">{medical_acc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Logical fallacies
        if fallacies:
            st.markdown(
                '<div class="card-title" style="margin:4px 0 10px">Identified Logical Fallacies</div>',
                unsafe_allow_html=True,
            )
            for f in fallacies:
                st.markdown(
                    f'<div class="fallacy-card">'
                    f'<div class="fallacy-name">Logical Fallacy</div>'
                    f'<div class="fallacy-desc">{f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Key misconceptions
        if misconceptions:
            st.markdown(
                '<div class="card-title" style="margin:4px 0 10px">Key Misconceptions</div>',
                unsafe_allow_html=True,
            )
            for m in misconceptions:
                st.markdown(
                    f'<div class="fallacy-card" style="background:#fff5f5;border-color:#fecaca">'
                    f'<div class="fallacy-desc" style="color:#7f1d1d">{m}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if recommend:
            st.info(f"**Expert Recommendation**: {recommend}")

    # Tab 2: Evidence
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)

        # Evidence summary
        if evidence_sum:
            st.markdown(
                f'<div class="card">'
                f'<div class="card-title">Medical Evidence Summary</div>'
                f'<div style="color:#475569;line-height:1.8">{evidence_sum}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # PubMed papers
        if pubmed_papers:
            st.markdown(
                '<div class="card-title" style="margin:4px 0 10px">Related Literature</div>',
                unsafe_allow_html=True,
            )
            for paper in pubmed_papers:
                journal = paper.get("journal", "")
                if any(k in journal for k in ["WHO","CDC","NIH","Nature","Lancet","NEJM"]):
                    badge = '<span class="badge badge-strong">Strong evidence</span><span class="badge badge-source">Authoritative</span>'
                else:
                    badge = '<span class="badge badge-journal">Moderate evidence</span><span class="badge badge-source">Journal</span>'

                link = (f'<a href="{paper["url"]}" target="_blank" '
                        f'style="color:#3b82f6;font-size:0.83rem;text-decoration:none">View article</a>'
                        if paper.get("url") else "")

                st.markdown(
                    f'<div class="evidence-card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">'
                    f'<div class="evidence-title">{paper["title"]}</div>'
                    f'<div style="white-space:nowrap">{badge}</div>'
                    f'</div>'
                    f'<div class="evidence-meta">'
                    f'{paper["journal"]} &nbsp;·&nbsp; {paper["authors"]} &nbsp;·&nbsp; {paper["year"]}'
                    f'</div>'
                    f'<div class="evidence-text">{paper["abstract"]}</div>'
                    f'<div style="margin-top:8px">{link}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif enable_pubmed:
            st.info("No directly related PubMed articles found; consider searching manually.")
            st.markdown("[Search on PubMed](https://pubmed.ncbi.nlm.nih.gov/)")

    # Tab 3: Risk Assessment
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(risk_badges_html(risk_level), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        risk_cls = {"Safe":"risk-card-safe","Misleading":"risk-card-mislead","Dangerous":"risk-card"}
        risk_text = risk_reason or medical_acc or "See Score Basis for details."
        st.markdown(
            f'<div class="{risk_cls.get(risk_level, "risk-card")}">{risk_text}</div>',
            unsafe_allow_html=True,
        )

        if recommend:
            st.markdown(
                f'<div class="card" style="margin-top:14px">'
                f'<div class="card-title">Expert Recommendation</div>'
                f'<div style="color:#475569;line-height:1.75">{recommend}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Tab 4: Scientific Rebuttal
    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)

        if rebuttal:
            st.markdown(
                f'<div class="card">'
                f'<div class="card-title">Detailed Scientific Rebuttal</div>'
                f'<div class="rebuttal-card">{rebuttal}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            social_text = f"{rebuttal[:100]}… #HealthMyth #ScienceFactCheck"
            st.markdown(
                f'<div class="card">'
                f'<div class="social-label">Social media version</div>'
                f'<div class="social-card">{social_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col_a, col_b = st.columns(2)
            with col_a:
                with st.expander("Copy full rebuttal"):
                    st.code(rebuttal, language=None)
            with col_b:
                with st.expander("Copy social media version"):
                    st.code(social_text, language=None)

    st.divider()
    if result.get("_parse_error"):
        with st.expander("⚙️ Debug info"):
            st.code(result.get("_raw_output", ""), language="text")
