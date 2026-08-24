import sys
import time
from pathlib import Path

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.openai_service import OpenAIService

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Islamic AI · Cache Demo",
    page_icon="☪️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp { background-color: #0d1117; color: #e6edf3; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Typography ── */
.app-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #e6edf3;
    letter-spacing: -0.02em;
    margin: 0 0 0.3rem 0;
    line-height: 1.2;
}
.app-subtitle {
    font-size: 0.82rem;
    color: #8b949e;
    display: flex;
    gap: 0.6rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 0;
}
.dot { color: #30363d; }
.divider { border: none; border-top: 1px solid #21262d; margin: 1rem 0 1.5rem 0; }

/* ── Section labels ── */
.section-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8b949e;
    margin: 0 0 0.6rem 0;
}

/* ── Result card ── */
.result-card {
    border-radius: 10px;
    padding: 1.4rem 1.5rem 1.2rem 1.5rem;
    margin-top: 0.75rem;
    border: 1px solid;
}
.card-l1  { background: #0d2818; border-color: #238636; }
.card-l2  { background: #0c1f3d; border-color: #1f6feb; }
.card-llm { background: #2d1a00; border-color: #d29922; }
.card-err { background: #2d0f0f; border-color: #da3633; }

.card-badge {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    margin-bottom: 0.75rem;
}
.badge-l1  { background:#0d3b22; color:#3fb950; border:1px solid #238636; }
.badge-l2  { background:#0c2461; color:#58a6ff; border:1px solid #1f6feb; }
.badge-llm { background:#3b1f00; color:#d29922; border:1px solid #d29922; }

.card-latency {
    font-size: 2.6rem;
    font-weight: 800;
    color: #e6edf3;
    line-height: 1;
    margin-bottom: 0.75rem;
}
.source-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0.35rem 0.8rem;
    border-radius: 20px;
    margin: 0.2rem 0.4rem 0.4rem 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.pill-quran { background: #0d3b22; color: #3fb950; border: 1px solid #238636; }
.pill-hadith { background: #0c2461; color: #58a6ff; border: 1px solid #1f6feb; }
.pill-tafseer { background: #3b1f00; color: #f2b705; border: 1px solid #d29922; }
.pill-general { background: #271052; color: #d2a8ff; border: 1px solid #8957e5; }
.sources-title {
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8b949e;
    margin: 0.6rem 0 0.4rem 0;
}
.card-detail {
    font-size: 0.8rem;
    color: #8b949e;
    margin-top: 0.75rem;
    line-height: 1.7;
}

/* ── Stats box ── */
.stat-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 0.75rem 0.85rem 0.75rem;
    text-align: center;
}
.stat-num  { font-size: 2rem; font-weight: 800; line-height: 1; }
.stat-name { font-size: 0.62rem; font-weight: 600; text-transform: uppercase;
             letter-spacing: 0.08em; color: #8b949e; margin-top: 0.35rem; }
.c-green { color: #3fb950; }
.c-blue  { color: #58a6ff; }
.c-amber { color: #d29922; }

/* ── Cost box ── */
.cost-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-top: 0.75rem;
}
.cost-label { font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
              letter-spacing: 0.1em; color: #8b949e; margin-bottom: 0.35rem; }
.cost-value { font-size: 1.6rem; font-weight: 800; color: #3fb950; line-height: 1; }
.cost-sub   { font-size: 0.7rem; color: #8b949e; margin-top: 0.25rem; }

/* ── Cache list ── */
.cache-entry {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 7px;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.35rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
}
.cache-q   { font-size: 0.78rem; color: #c9d1d9; overflow: hidden;
             text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.cache-src { font-size: 0.68rem; color: #8b949e; white-space: nowrap; }

/* ── Clear button ── */
.stButton > button {
    background: #21262d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    width: 100% !important;
    padding: 0.5rem !important;
    transition: border-color 0.15s;
}
.stButton > button:hover {
    border-color: #da3633 !important;
    color: #f85149 !important;
}

/* ── Classify button ── */
div[data-testid="stForm"] .stButton > button {
    background: #238636 !important;
    color: #fff !important;
    border: none !important;
    font-size: 0.875rem !important;
    padding: 0.6rem !important;
}
div[data-testid="stForm"] .stButton > button:hover {
    background: #2ea043 !important;
    color: #fff !important;
    border: none !important;
}

/* ── Input ── */
.stTextInput > div > div > input {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2ea043 !important;
    box-shadow: 0 0 0 3px rgba(46,160,67,0.12) !important;
    outline: none !important;
}

/* ── Progress bar ── */
.stProgress > div > div { background-color: #238636 !important; }

/* ── Expander ── */
.streamlit-expanderHeader { color: #8b949e !important; font-size: 0.8rem !important; }
.streamlit-expanderContent { background: #161b22 !important; font-size: 0.8rem !important; color: #c9d1d9 !important; }

div[data-testid="stHorizontalBlock"] { gap: 1.5rem; }
div[data-testid="column"] { min-width: 0; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "service" not in st.session_state:
    st.session_state.service = OpenAIService()
if "history" not in st.session_state:
    st.session_state.history = []
if "stats" not in st.session_state:
    st.session_state.stats = {"L1": 0, "L2": 0, "LLM": 0}
if "last_result" not in st.session_state:
    st.session_state.last_result = None

svc: OpenAIService = st.session_state.service
COST_PER_CALL = 0.0006

# ── Helpers ───────────────────────────────────────────────────────────────────
def pill(source_name: str) -> str:
    s = source_name.lower().strip()
    if s == "quran":
        return '<span class="source-pill pill-quran">📖 Quran</span>'
    elif s == "hadith":
        return '<span class="source-pill pill-hadith">🕌 Hadith</span>'
    elif s == "tafseer":
        return '<span class="source-pill pill-tafseer">👨‍🏫 Tafseer</span>'
    else:
        return '<span class="source-pill pill-general">📚 General Islamic Info</span>'

def semantic_cache_items():
    return [(q, list(cls.required_sources)) for _, cls, q in svc._semantic_cache]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 class="app-title">☪️ &nbsp;Islamic AI — Query Classification Cache</h1>
<p class="app-subtitle">
    <span>2-Layer Hybrid Caching System</span>
    <span class="dot">·</span>
    <span>Layer 1: Exact Match (0ms)</span>
    <span class="dot">·</span>
    <span>Layer 2: Semantic Similarity (~15ms)</span>
    <span class="dot">·</span>
    <span>Layer 3: LLM Fallback (~400ms)</span>
</p>
<hr class="divider">
""", unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────
left, right = st.columns([1.65, 1], gap="large")

# ══════════════════════════════════════════════════════
# LEFT — Input + Result + History
# ══════════════════════════════════════════════════════
with left:

    st.markdown('<p class="section-label">Enter your query</p>', unsafe_allow_html=True)

    with st.form("qform", clear_on_submit=False):
        query_input = st.text_input(
            label="query",
            placeholder="e.g. What did Prophet Muhammad say about honesty?",
            label_visibility="collapsed",
        )
        classify_btn = st.form_submit_button("Classify Query ▶", use_container_width=True)

    if classify_btn and query_input.strip():
        with st.spinner("Processing..."):
            emb = svc.embed_query(query_input.strip())
            res = svc.classify_query_with_metadata(query_input.strip(), emb)

        if res.get("status") == "success":
            res["query"] = query_input.strip()
            st.session_state.last_result = res
            st.session_state.stats[res["cache_layer"]] += 1
            st.session_state.history.insert(0, res)
            if len(st.session_state.history) > 20:
                st.session_state.history.pop()
        else:
            st.session_state.last_result = {"status": "error", "message": res.get("message", "Unknown error")}

    # ── Result card ────────────────────────────────────────────
    r = st.session_state.last_result

    if r is None:
        st.markdown("""
        <div style="margin-top:1rem; padding:2rem 1.5rem; background:#161b22;
                    border:1px dashed #30363d; border-radius:10px; text-align:center;">
            <p style="color:#8b949e; margin:0; font-size:0.875rem;">
                Enter a query and click <strong style="color:#c9d1d9;">Classify Query</strong>
                to see which cache layer responds.
            </p>
        </div>
        """, unsafe_allow_html=True)

    elif r.get("status") == "error":
        st.markdown(f"""
        <div class="result-card card-err">
            <div class="card-badge" style="background:#2d0f0f;color:#f85149;border:1px solid #da3633;">
                Error
            </div>
            <div style="color:#f85149;font-size:0.875rem;">{r['message']}</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        layer = r["cache_layer"]
        card_cls = {"L1": "card-l1", "L2": "card-l2", "LLM": "card-llm"}[layer]
        badge_cls = {"L1": "badge-l1", "L2": "badge-l2", "LLM": "badge-llm"}[layer]

        # Full descriptive label
        badge_text = {
            "L1":  "⚡ L1 — Exact Match Cache Hit",
            "L2":  "🔵 L2 — Approximate / Semantic Cache Hit",
            "LLM": "🤖 L3 — LLM Fallback",
        }[layer]

        sources = list(r["classification"].required_sources)
        latency_str = f"{r['latency_ms']:.1f} ms" if r["latency_ms"] >= 1 else "< 1 ms"
        sources_html = "".join(pill(s) for s in sources)

        if layer == "L1":
            detail = (
                f'✅ Matched exactly: <em>"{r["matched_query"]}"</em><br>'
                f'No OpenAI API call made.'
            )
        elif layer == "L2":
            pct = int(r["similarity_score"] * 100)
            detail = (
                f'Cosine similarity: <strong style="color:#e6edf3;">{r["similarity_score"]}</strong> '
                f'({pct}% match)<br>'
                f'Matched cached query: <em>"{r["matched_query"]}"</em><br>'
                f'No OpenAI API call made.'
            )
        else:
            detail = (
                'OpenAI <code>gpt-4.1-nano</code> called.<br>'
                'Result stored in Layer 1 (exact) &amp; Layer 2 (semantic) cache.'
            )

        st.markdown(f"""
        <div class="result-card {card_cls}">
            <span class="card-badge {badge_cls}">{badge_text}</span>
            <div class="card-latency">{latency_str}</div>
            <div class="sources-title">Required Islamic Sources</div>
            <div style="margin-bottom:0.5rem;">{sources_html}</div>
            <div class="card-detail">{detail}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Query history ───────────────────────────────────────────
    if st.session_state.history:
        st.markdown('<p class="section-label" style="margin-top:2rem;">Query History</p>',
                    unsafe_allow_html=True)

        layer_badge_map = {
            "L1":  ('<span style="background:#0d2818;color:#3fb950;border:1px solid #238636;'
                    'border-radius:12px;padding:0.15rem 0.55rem;font-size:0.68rem;font-weight:700;">'
                    '⚡ L1 Exact</span>'),
            "L2":  ('<span style="background:#0c1f3d;color:#58a6ff;border:1px solid #1f6feb;'
                    'border-radius:12px;padding:0.15rem 0.55rem;font-size:0.68rem;font-weight:700;">'
                    '🔵 L2 Semantic</span>'),
            "LLM": ('<span style="background:#2d1a00;color:#d29922;border:1px solid #d29922;'
                    'border-radius:12px;padding:0.15rem 0.55rem;font-size:0.68rem;font-weight:700;">'
                    '🤖 LLM Fallback</span>'),
        }

        # Header row
        h1, h2, h3, h4, h5 = st.columns([0.4, 3, 2, 1.2, 2.5])
        for col, label in zip([h1, h2, h3, h4, h5], ["#", "Query", "Layer", "Latency", "Sources"]):
            col.markdown(
                f'<p style="font-size:0.62rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.1em;color:#8b949e;margin:0 0 4px 0;">{label}</p>',
                unsafe_allow_html=True
            )

        st.markdown('<hr style="border:none;border-top:1px solid #21262d;margin:0 0 4px 0;">', unsafe_allow_html=True)

        for i, h in enumerate(st.session_state.history[:10]):
            c1, c2, c3, c4, c5 = st.columns([0.4, 3, 2, 1.2, 2.5])
            lat_str = f"{h['latency_ms']:.0f} ms" if h["latency_ms"] >= 1 else "< 1 ms"
            srcs = ", ".join(h["classification"].required_sources)
            q_display = h["query"][:44] + "…" if len(h["query"]) > 44 else h["query"]

            c1.markdown(f'<p style="font-size:0.78rem;color:#8b949e;margin:0;">{i+1}</p>', unsafe_allow_html=True)
            c2.markdown(f'<p style="font-size:0.78rem;color:#c9d1d9;margin:0;" title="{h["query"]}">{q_display}</p>', unsafe_allow_html=True)
            c3.markdown(layer_badge_map[h["cache_layer"]], unsafe_allow_html=True)
            c4.markdown(f'<p style="font-size:0.78rem;color:#e6edf3;margin:0;">{lat_str}</p>', unsafe_allow_html=True)
            c5.markdown(f'<p style="font-size:0.72rem;color:#8b949e;margin:0;">{srcs}</p>', unsafe_allow_html=True)

            st.markdown('<hr style="border:none;border-top:1px solid #21262d;margin:2px 0;">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# RIGHT — Stats + Cache Inspector
# ══════════════════════════════════════════════════════
with right:

    # ── Live stats ─────────────────────────────────────────────
    st.markdown('<p class="section-label">Live Cache Stats</p>', unsafe_allow_html=True)

    s = st.session_state.stats
    total = s["L1"] + s["L2"] + s["LLM"]

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-num c-green">{s['L1']}</div>
        <div class="stat-name">L1<br>Exact Match</div>
    </div>""", unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-num c-blue">{s['L2']}</div>
        <div class="stat-name">L2<br>Approx. Match</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-num c-amber">{s['LLM']}</div>
        <div class="stat-name">LLM<br>Fallback</div>
    </div>""", unsafe_allow_html=True)

    # ── Hit rate ────────────────────────────────────────────────
    st.markdown('<p class="section-label" style="margin-top:1.1rem;">Cache Hit Rate</p>', unsafe_allow_html=True)
    if total > 0:
        hits = s["L1"] + s["L2"]
        rate = hits / total
        st.progress(rate, text=f"{int(rate*100)}%  ·  {hits} of {total} queries served from cache")
    else:
        st.markdown('<p style="font-size:0.78rem;color:#8b949e;margin:0;">No queries yet.</p>', unsafe_allow_html=True)

    # ── Cost saved ──────────────────────────────────────────────
    saved = (s["L1"] + s["L2"]) * COST_PER_CALL
    st.markdown(f"""
    <div class="cost-box">
        <div class="cost-label">Estimated API Cost Saved</div>
        <div class="cost-value">${saved:.4f}</div>
        <div class="cost-sub">{s['L1']+s['L2']} API call(s) avoided · ~$0.0006 per call</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Semantic cache inspector ────────────────────────────────
    st.markdown('<p class="section-label" style="margin-top:1.1rem;">Semantic Cache Contents (Layer 2)</p>',
                unsafe_allow_html=True)

    items = semantic_cache_items()
    if not items:
        st.markdown('<p style="font-size:0.78rem;color:#8b949e;margin:0;">Empty — populated after each LLM call.</p>',
                    unsafe_allow_html=True)
    else:
        for q, srcs in items:
            srcs_str = ", ".join(srcs)
            st.markdown(f"""
            <div class="cache-entry">
                <span class="cache-q">"{q}"</span>
                <span class="cache-src">{srcs_str}</span>
            </div>""", unsafe_allow_html=True)

    # ── Clear ───────────────────────────────────────────────────
    st.markdown("<div style='margin-top:0.75rem;'>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All Caches", use_container_width=True):
        svc._classification_cache.clear()
        svc._semantic_cache.clear()
        if svc.redis_client:
            try:
                for k in svc.redis_client.keys("exact_cache:*"):
                    svc.redis_client.delete(k)
            except Exception:
                pass
        if svc.qdrant_service:
            try:
                svc.qdrant_service.client.delete_collection(settings.CLASSIFICATION_CACHE_COLLECTION_NAME)
                svc.qdrant_service.ensure_cache_collection()
            except Exception:
                pass
        st.session_state.stats  = {"L1": 0, "L2": 0, "LLM": 0}
        st.session_state.history = []
        st.session_state.last_result = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── How it works ────────────────────────────────────────────
    with st.expander("How It Works"):
        st.markdown("""
**Layer 1 — Exact Match (Redis / RAM)** `~0-1ms`
Key-Value lookup in Redis (or in-memory TTL cache fallback). Same query → instant return, zero API cost. Persistent & scalable across worker instances.

**Layer 2 — Approximate / Semantic Match (Qdrant Collection)** `~10-15ms`
Vector ANN search over Qdrant `classification_cache` collection. Threshold **0.85**. Paraphrased queries (same meaning, different words) return cached classification without calling OpenAI.

**Layer 3 — LLM Fallback (OpenAI gpt-4.1-nano)** `~400ms`
Calls OpenAI structured output (`QueryClassificationSchema`). The classification is saved into both Redis & Qdrant vector collection for future queries.
""")
