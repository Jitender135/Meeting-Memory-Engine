"""
app.py — Streamlit frontend for Meeting Memory Engine.
Design: Monochrome internal tool. No gradients, no emojis in UI, no AI aesthetics.
Inspired by Linear, Vercel, Raycast.
"""

import httpx
import streamlit as st
from datetime import date

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meeting Memory",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #0a0a0a;
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    color: #e8e8e8;
    font-size: 14px;
}

#MainMenu, footer, header, [data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f0f0f;
    border-right: 1px solid #1c1c1c;
    padding: 0;
}
[data-testid="stSidebar"] > div:first-child { padding: 28px 20px; }

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid #1c1c1c;
}
.brand-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #4f6ef7;
    flex-shrink: 0;
}
.brand-name {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.2px;
}

.nav-label {
    font-size: 10px;
    font-weight: 600;
    color: #333333;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
    margin-top: 24px;
    display: block;
}

.status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #555555;
    padding: 8px 0;
}
.dot-green  { width:6px; height:6px; border-radius:50%; background:#22c55e; flex-shrink:0; }
.dot-red    { width:6px; height:6px; border-radius:50%; background:#ef4444; flex-shrink:0; }
.dot-yellow { width:6px; height:6px; border-radius:50%; background:#f59e0b; flex-shrink:0; }

.meeting-item {
    padding: 9px 0;
    border-bottom: 1px solid #141414;
}
.meeting-item-title {
    font-size: 12px;
    font-weight: 500;
    color: #cccccc;
    line-height: 1.4;
}
.meeting-item-date {
    font-size: 11px;
    color: #444444;
    margin-top: 2px;
    font-variant-numeric: tabular-nums;
}

/* ── Main content ── */
[data-testid="stMain"] { background: #0a0a0a; }
.block-container { padding: 40px 48px 40px 48px !important; max-width: 860px; }

.page-header {
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid #1c1c1c;
}
.page-title {
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.4px;
    line-height: 1.3;
}
.page-desc {
    font-size: 13px;
    color: #555555;
    margin-top: 6px;
    line-height: 1.5;
}

/* ── Input area ── */
.input-label {
    font-size: 11px;
    font-weight: 600;
    color: #444444;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    display: block;
}

.stTextArea textarea {
    background: #111111 !important;
    border: 1px solid #222222 !important;
    border-radius: 6px !important;
    color: #e8e8e8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    resize: none !important;
    padding: 12px 14px !important;
    transition: border-color 0.15s !important;
}
.stTextArea textarea::placeholder { color: #383838 !important; }
.stTextArea textarea:focus {
    border-color: #4f6ef7 !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextArea"] label { display: none !important; }

/* ── Buttons ── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 9px 20px !important;
    cursor: pointer !important;
    transition: opacity 0.15s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

div[data-testid="column"]:first-child .stButton > button {
    background: #4f6ef7 !important;
    color: #ffffff !important;
    width: 100% !important;
    letter-spacing: 0.02em !important;
    font-size: 13px !important;
}
div[data-testid="column"]:last-child .stButton > button {
    background: #1a1a1a !important;
    color: #888888 !important;
    border: 1px solid #222222 !important;
    width: 100% !important;
}

/* ── Sidebar button ── */
[data-testid="stSidebar"] .stButton > button {
    background: #1a1a1a !important;
    color: #888888 !important;
    border: 1px solid #222222 !important;
    font-size: 12px !important;
    padding: 7px 14px !important;
    width: 100% !important;
}

/* ── Filter toggle ── */
.stToggle { margin: 4px 0 !important; }
[data-testid="stToggle"] label { font-size: 12px !important; color: #555555 !important; }

/* ── Slider ── */
[data-testid="stSlider"] label { font-size: 12px !important; color: #555555 !important; }
.stSlider [data-baseweb="slider"] { margin-top: 8px; }

/* ── Answer section ── */
.answer-label {
    font-size: 10px;
    font-weight: 600;
    color: #333333;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
    margin-top: 28px;
    display: block;
}

.answer-block {
    background: #111111;
    border: 1px solid #1c1c1c;
    border-left: 2px solid #4f6ef7;
    border-radius: 6px;
    padding: 18px 20px;
    font-size: 14px;
    line-height: 1.75;
    color: #d4d4d4;
}

/* ── Sources ── */
.sources-label {
    font-size: 10px;
    font-weight: 600;
    color: #333333;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 24px;
    margin-bottom: 12px;
    display: block;
}

.source-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border: 1px solid #1a1a1a;
    border-radius: 6px;
    margin-bottom: 6px;
    background: #0f0f0f;
}
.source-left {}
.source-name {
    font-size: 13px;
    font-weight: 500;
    color: #cccccc;
}
.source-date {
    font-size: 11px;
    color: #444444;
    margin-top: 2px;
    font-variant-numeric: tabular-nums;
}
.source-score {
    font-size: 11px;
    font-weight: 500;
    color: #4f6ef7;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    padding: 3px 10px;
    border: 1px solid #1e2a5e;
    border-radius: 4px;
    background: #0d1232;
}
            
/* ── Action items table ── */
.action-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
}
.action-table th {
    font-size: 10px;
    font-weight: 600;
    color: #333333;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #1a1a1a;
}
.action-table td {
    font-size: 13px;
    color: #cccccc;
    padding: 10px 12px;
    border-bottom: 1px solid #141414;
    vertical-align: top;
    line-height: 1.5;
}
.action-table tr:last-child td { border-bottom: none; }
.owner-cell {
    font-weight: 500;
    color: #ffffff;
    white-space: nowrap;
}
.due-cell {
    color: #555555;
    font-size: 12px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.action-wrap {
    background: #0f0f0f;
    border: 1px solid #1a1a1a;
    border-radius: 6px;
    overflow: hidden;
    margin-top: 4px;
}            

/* ── Eval scores ── */
.eval-wrap {
    background: #0f0f0f;
    border: 1px solid #1a1a1a;
    border-radius: 6px;
    padding: 16px 20px;
    margin-top: 4px;
}
.eval-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #141414;
}
.eval-row:last-child { border-bottom: none; }
.eval-label {
    font-size: 12px;
    font-weight: 500;
    color: #888888;
}
.eval-reason {
    font-size: 11px;
    color: #444444;
    margin-top: 2px;
    max-width: 480px;
}
.eval-score-high { color: #22c55e; font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
.eval-score-mid  { color: #f59e0b; font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
.eval-score-low  { color: #ef4444; font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
.overall-score {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 12px;
    margin-bottom: 4px;
    border-bottom: 1px solid #1a1a1a;
}
.overall-label { font-size: 11px; font-weight: 600; color: #555555; text-transform: uppercase; letter-spacing: 0.08em; }
.overall-value { font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }

/* ── Empty state ── */
.empty-wrap {
    padding: 24px 0 32px;
    border-top: 1px solid #141414;
    margin-top: 16px;
}
.empty-heading {
    font-size: 14px;
    font-weight: 500;
    color: #333333;
    margin-bottom: 20px;
}
.example-item {
    font-size: 13px;
    color: #333333;
    padding: 10px 14px;
    border: 1px solid #161616;
    border-radius: 5px;
    margin-bottom: 6px;
    font-style: italic;
    cursor: default;
}

/* ── History ── */
.history-item {
    font-size: 12px;
    color: #444444;
    padding: 7px 0;
    border-bottom: 1px solid #141414;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.history-item::before {
    content: '↳ ';
    color: #2a2a2a;
}

/* ── Warning / error ── */
[data-testid="stAlert"] {
    background: #130d0d !important;
    border: 1px solid #3a1a1a !important;
    border-radius: 6px !important;
    color: #cc4444 !important;
    font-size: 13px !important;
}
            
/* ── Chat interface ── */
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 8px;
    margin-bottom: 24px;
}
.chat-bubble-user {
    align-self: flex-end;
    background: #1a2a4a;
    border: 1px solid #1e3a6e;
    border-radius: 12px 12px 2px 12px;
    padding: 12px 16px;
    max-width: 75%;
    font-size: 14px;
    color: #e2e8f0;
    line-height: 1.6;
}
.chat-bubble-assistant {
    align-self: flex-start;
    background: #111111;
    border: 1px solid #1c1c1c;
    border-left: 2px solid #4f6ef7;
    border-radius: 2px 12px 12px 12px;
    padding: 12px 16px;
    max-width: 85%;
    font-size: 14px;
    color: #d4d4d4;
    line-height: 1.75;
}
.chat-sources {
    font-size: 11px;
    color: #333333;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #1a1a1a;
}
.chat-source-item {
    display: inline-block;
    background: #0f0f0f;
    border: 1px solid #1a1a1a;
    border-radius: 4px;
    padding: 2px 8px;
    margin-right: 6px;
    margin-top: 4px;
    font-size: 11px;
    color: #444444;
}
.mode-tab {
    display: inline-block;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 16px;
    border-radius: 6px;
    cursor: pointer;
    margin-right: 6px;
}
.mode-tab-active {
    background: #4f6ef7;
    color: #ffffff;
}
.mode-tab-inactive {
    background: #1a1a1a;
    color: #555555;
    border: 1px solid #222222;
}
            
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────
import os
API_BASE = os.getenv("API_BASE", "http://localhost:8000")


# ── API helpers ────────────────────────────────────────────────────
HEADERS = {"X-API-Key": "mme-secret-2024"}

# Force IPv4 — Streamlit Cloud has IPv6 issues with external APIs
import httpx
transport = httpx.HTTPTransport(local_address="0.0.0.0")
client = httpx.Client(transport=transport, timeout=30)

def api_health() -> dict:
    try:
        r = client.get(f"{API_BASE}/health", timeout=5)
        return r.json()
    except Exception:
        return {"status": "error", "pipeline": "unreachable"}

def api_meetings() -> list:
    try:
        r = client.get(f"{API_BASE}/meetings", headers=HEADERS, timeout=5)
        return r.json().get("meetings", [])
    except Exception:
        return []

def api_query(question: str, date_from=None, date_to=None, top_k=3) -> dict:
    payload = {"question": question, "top_k": top_k}
    if date_from: payload["date_from"] = str(date_from)
    if date_to:   payload["date_to"]   = str(date_to)
    try:
        r = client.post(f"{API_BASE}/query", json=payload, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_action_items(question: str, date_from=None, date_to=None) -> dict:
    payload = {"question": question}
    if date_from: payload["date_from"] = str(date_from)
    if date_to:   payload["date_to"]   = str(date_to)
    try:
        r = client.post(f"{API_BASE}/action-items", json=payload, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_ingest() -> dict:
    try:
        r = client.post(f"{API_BASE}/ingest", headers=HEADERS, timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_evaluate(question: str, answer: str, contexts: list) -> dict:
    try:
        r = client.post(
            f"{API_BASE}/evaluate",
            json={"question": question, "answer": answer, "contexts": contexts},
            headers=HEADERS,
            timeout=30,
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_chat(question: str, history: list, date_from=None, date_to=None, top_k=3) -> dict:
    payload = {"question": question, "history": history, "top_k": top_k}
    if date_from: payload["date_from"] = str(date_from)
    if date_to:   payload["date_to"]   = str(date_to)
    try:
        r = client.post(f"{API_BASE}/chat", json=payload, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Session state ──────────────────────────────────────────────────
if "history"       not in st.session_state: st.session_state.history       = []
if "last_result"   not in st.session_state: st.session_state.last_result   = None
if "last_question" not in st.session_state: st.session_state.last_question = ""
if "chat_history"  not in st.session_state: st.session_state.chat_history  = []
if "mode"          not in st.session_state: st.session_state.mode          = "search"
if "chat_input_key" not in st.session_state: st.session_state.chat_input_key = 0

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:

    # Brand
    st.markdown("""
    <div class="brand">
        <div class="brand-dot"></div>
        <span class="brand-name">Meeting Memory</span>
    </div>
    """, unsafe_allow_html=True)

    # Status
    st.markdown('<span class="nav-label">System</span>', unsafe_allow_html=True)
    health = api_health()
    if health.get("status") == "ok" and health.get("pipeline") == "ready":
        st.markdown('<div class="status-row"><div class="dot-green"></div>API connected &middot; Pipeline ready</div>', unsafe_allow_html=True)
    elif health.get("status") == "ok":
        st.markdown('<div class="status-row"><div class="dot-yellow"></div>API connected &middot; Not ingested</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-row"><div class="dot-red"></div>API unreachable</div>', unsafe_allow_html=True)

    # Re-ingest
    st.markdown('<span class="nav-label">Pipeline</span>', unsafe_allow_html=True)
    if st.button("Re-index transcripts", use_container_width=True):
        with st.spinner("Indexing..."):
            result = api_ingest()
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"{result.get('files')} files · {result.get('chunks')} chunks indexed")

    # Meetings list
    st.markdown('<span class="nav-label">Indexed Meetings</span>', unsafe_allow_html=True)
    meetings = api_meetings()
    if meetings:
        for m in meetings:
            st.markdown(
                f'<div class="meeting-item">'
                f'<div class="meeting-item-title">{m["title"]}</div>'
                f'<div class="meeting-item-date">{m["date"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="status-row">No meetings indexed.</div>', unsafe_allow_html=True)

    # Filters
    st.markdown('<span class="nav-label">Filters</span>', unsafe_allow_html=True)
    use_filter = st.toggle("Filter by date range", value=False)
    date_from, date_to = None, None
    if use_filter:
        date_from = st.date_input("From", value=date(2024, 1, 1), label_visibility="visible")
        date_to   = st.date_input("To",   value=date.today(),     label_visibility="visible")

    st.markdown('<span class="nav-label">Retrieval</span>', unsafe_allow_html=True)
    top_k = st.slider("Chunks to retrieve", min_value=1, max_value=6, value=3)

    # History
    if st.session_state.history:
        st.markdown('<span class="nav-label">Recent</span>', unsafe_allow_html=True)
        for q in reversed(st.session_state.history[-6:]):
            st.markdown(
                f'<div class="history-item">{q[:52]}{"..." if len(q) > 52 else ""}</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════
# MAIN PANEL
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <div class="page-title">Query your meetings</div>
    <div class="page-desc">Ask anything across all indexed transcripts. Answers are grounded in source documents and cited by meeting.</div>
</div>
""", unsafe_allow_html=True)

# ── Mode tabs ─────────────────────────────────────────────────────
col_s, col_c, _ = st.columns([1, 1, 5])
with col_s:
    if st.button("Search", key="mode_search", use_container_width=True):
        st.session_state.mode = "search"
with col_c:
    if st.button("Chat", key="mode_chat", use_container_width=True):
        st.session_state.mode = "chat"

st.markdown(
    f'<div style="font-size:11px;color:#333333;margin-bottom:16px;margin-top:4px;">'
    f'Mode: <span style="color:#4f6ef7;font-weight:500;">'
    f'{"Search — single query" if st.session_state.mode == "search" else "Chat — conversational memory"}'
    f'</span></div>',
    unsafe_allow_html=True,
)

# ── SEARCH MODE ───────────────────────────────────────────────────
if st.session_state.mode == "search":

    st.markdown('<span class="input-label">Question</span>', unsafe_allow_html=True)
    question = st.text_area(
        label="question_input",
        placeholder="What did we decide about the mobile app launch?",
        height=88,
        label_visibility="collapsed",
    )

    col_search, col_clear = st.columns([5, 1])
    with col_search:
        search_clicked = st.button("Search", use_container_width=True)
    with col_clear:
        clear_clicked = st.button("Clear", use_container_width=True)

    if clear_clicked:
        st.session_state.last_result   = None
        st.session_state.last_question = ""
        st.rerun()

    if search_clicked:
        if not question.strip():
            st.warning("Enter a question to search.")
        else:
            with st.spinner("Searching..."):
                result = api_query(
                    question=question.strip(),
                    date_from=date_from if use_filter else None,
                    date_to=date_to     if use_filter else None,
                    top_k=top_k,
                )
            st.session_state.last_result   = result
            st.session_state.last_question = question.strip()
            if question.strip() not in st.session_state.history:
                st.session_state.history.append(question.strip())

    if st.session_state.last_result:
        result = st.session_state.last_result
        if "error" in result:
            st.error(f"Request failed: {result['error']}")
        else:
            st.markdown('<span class="answer-label">Answer</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="answer-block">{result["answer"]}</div>', unsafe_allow_html=True)

            sources = result.get("sources", [])
            if sources:
                st.markdown('<span class="sources-label">Sources</span>', unsafe_allow_html=True)
                for s in sources:
                    score_pct = round(s["score"] * 100)
                    st.markdown(
                        f'<div class="source-row">'
                        f'  <div class="source-left">'
                        f'    <div class="source-name">{s["title"]}</div>'
                        f'    <div class="source-date">{s["date"]}</div>'
                        f'  </div>'
                        f'  <div class="source-score">{score_pct}% match</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<span class="sources-label">Action Items</span>', unsafe_allow_html=True)
            with st.spinner("Extracting action items..."):
                ai_result = api_action_items(
                    question=st.session_state.last_question,
                    date_from=date_from if use_filter else None,
                    date_to=date_to     if use_filter else None,
                )
            items = ai_result.get("action_items", [])
            if items:
                rows = ""
                for item in items:
                    rows += (
                        f'<tr>'
                        f'<td class="owner-cell">{item.get("owner","—")}</td>'
                        f'<td>{item.get("task","—")}</td>'
                        f'<td class="due-cell">{item.get("due","—")}</td>'
                        f'<td class="due-cell">{item.get("meeting","—")}</td>'
                        f'</tr>'
                    )
                st.markdown(
                    f'<div class="action-wrap"><table class="action-table">'
                    f'<thead><tr><th>Owner</th><th>Task</th><th>Due</th><th>Meeting</th></tr></thead>'
                    f'<tbody>{rows}</tbody></table></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div style="font-size:13px;color:#333333;padding:12px 0;">No action items found.</div>', unsafe_allow_html=True)

            st.markdown('<span class="sources-label">Pipeline Quality</span>', unsafe_allow_html=True)
            with st.spinner("Evaluating response quality..."):
                contexts    = [s.get("excerpt", s.get("title", "")) for s in result.get("sources", [])]
                eval_result = api_evaluate(
                    question=st.session_state.last_question,
                    answer=result["answer"],
                    contexts=contexts,
                )
            if "error" not in eval_result and eval_result.get("status") == "success":
                overall       = eval_result.get("overall", 0)
                overall_class = "eval-score-high" if overall >= 0.7 else "eval-score-mid" if overall >= 0.4 else "eval-score-low"
                metrics = [
                    ("Faithfulness",      eval_result.get("faithfulness",      {})),
                    ("Answer Relevance",  eval_result.get("answer_relevancy",  {})),
                    ("Context Precision", eval_result.get("context_precision", {})),
                ]
                rows = ""
                for label, m in metrics:
                    score       = m.get("score", 0)
                    reason      = m.get("reason", "")
                    score_class = "eval-score-high" if score >= 0.7 else "eval-score-mid" if score >= 0.4 else "eval-score-low"
                    rows += (
                        f'<div class="eval-row">'
                        f'  <div><div class="eval-label">{label}</div>'
                        f'  <div class="eval-reason">{reason}</div></div>'
                        f'  <div class="{score_class}">{score:.2f}</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div class="eval-wrap">'
                    f'  <div class="overall-score"><span class="overall-label">Overall</span>'
                    f'  <span class="{overall_class} overall-value">{overall:.2f}</span></div>'
                    f'  {rows}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown("""
        <div class="empty-wrap">
            <div class="empty-heading">Try one of these</div>
            <div class="example-item">What did we decide about the mobile app launch?</div>
            <div class="example-item">What action items were assigned in Q1?</div>
            <div class="example-item">Who committed to the Android performance fix?</div>
            <div class="example-item">What was the pricing model we agreed on?</div>
        </div>
        """, unsafe_allow_html=True)


# ── CHAT MODE ─────────────────────────────────────────────────────
else:
    # Render chat history
    if st.session_state.chat_history:
        st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
        for turn in st.session_state.chat_history:
            if turn["role"] == "user":
                st.markdown(
                    f'<div style="display:flex;justify-content:flex-end;margin-bottom:8px;">'
                    f'<div class="chat-bubble-user">{turn["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                sources_html = ""
                if turn.get("sources"):
                    sources_html = '<div class="chat-sources">'
                    for s in turn["sources"]:
                        sources_html += f'<span class="chat-source-item">{s["title"]} · {s["date"]}</span>'
                    sources_html += '</div>'
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<div class="chat-bubble-assistant">{turn["content"]}{sources_html}</div></div>',
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-wrap">
            <div class="empty-heading">Start a conversation</div>
            <div class="example-item">What did we decide about the mobile app launch?</div>
            <div class="example-item">Then ask: Who was responsible for that?</div>
            <div class="example-item">Or: When was the deadline for it?</div>
        </div>
        """, unsafe_allow_html=True)

    # Chat input
    st.markdown('<span class="input-label">Message</span>', unsafe_allow_html=True)
    chat_question = st.text_area(
        label="chat_input",
        placeholder="Ask a follow-up question...",
        height=72,
        label_visibility="collapsed",
        key=f"chat_input_{st.session_state.chat_input_key}",
    )

    col_send, col_reset = st.columns([5, 1])
    with col_send:
        send_clicked = st.button("Send", use_container_width=True, key="chat_send")
    with col_reset:
        reset_clicked = st.button("Reset", use_container_width=True, key="chat_reset")

    if reset_clicked:
        st.session_state.chat_history = []
        st.rerun()

    if send_clicked:
        if not chat_question.strip():
            st.warning("Enter a message.")
        else:
            # Build history for API
            api_history = [
                {"role": t["role"], "content": t["content"]}
                for t in st.session_state.chat_history
            ]
            st.session_state.chat_input_key += 1
            with st.spinner("Thinking..."):
                result = api_chat(
                    question=chat_question.strip(),
                    history=api_history,
                    date_from=date_from if use_filter else None,
                    date_to=date_to     if use_filter else None,
                )

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.session_state.chat_history.append({
                    "role":    "user",
                    "content": chat_question.strip(),
                })
                st.session_state.chat_history.append({
                    "role":    "assistant",
                    "content": result["answer"],
                    "sources": result.get("sources", []),
                })
                st.rerun()