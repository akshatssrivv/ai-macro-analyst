import streamlit as st
from datetime import datetime, timedelta
import uuid

# In-memory storage (reset each app restart)
RUNS = []
ARTICLES = []
EVENTS = []
BRIEFS = []

def run_once():
    run_id = uuid.uuid4().hex[:8]
    started = datetime.utcnow()

    # dummy collect
    articles = [
        {"source": "DUMMY", "url": "https://example.com/eu-budget",
         "published_at": started, "country": "EU", "headline": "EU budget talks progress (dummy)"},
        {"source": "DUMMY", "url": "https://example.com/aft-auction",
         "published_at": started, "country": "FR", "headline": "AFT schedules OAT auction (dummy)"},
    ]
    events = [
        {"date_time": started + timedelta(hours=2), "country": "US",
         "type": "macro release", "details": "NFP at 13:30 UK (dummy)",
         "source_link": "https://www.bls.gov/", "status": "upcoming"}
    ]
    brief = {
        "run_id": run_id,
        "created_at": started,
        "what_happened": "; ".join(a["headline"] for a in articles),
        "why_it_matters": "Scaffold test — shows dummy data end-to-end.",
        "action_bias": "Observe",
        "confidence": 0.5,
        "risks": "None",
        "links": [a["url"] for a in articles],
    }

    # persist in memory
    RUNS.append({"run_id": run_id, "started_at": started, "items_in": len(articles)})
    ARTICLES.extend(articles)
    EVENTS.extend(events)
    BRIEFS.append(brief)

    return {"run_id": run_id, "items_in": len(articles)}

# ------------------ UI ------------------

st.set_page_config(page_title="AI Macro News & Events Analyst", layout="wide")
st.title("AI Macro News & Events Analyst — Demo Skeleton")

tabs = st.tabs(["Briefs", "Run Now", "News Archive", "Events", "Ops"])

# Briefs
with tabs[0]:
    st.subheader("Top items")
    if not BRIEFS:
        st.info("No briefs yet. Use Run Now.")
    for b in reversed(BRIEFS[-5:]):
        st.markdown(f"**What**: {b['what_happened']}")
        st.markdown(f"**Why**: {b['why_it_matters']}")
        st.write("---")

# Run Now
with tabs[1]:
    st.subheader("Ad-hoc run")
    if st.button("Run pipeline once"):
        result = run_once()
        st.success(result)

# Archive
with tabs[2]:
    st.subheader("News Archive")
    if not ARTICLES:
        st.info("No articles yet.")
    for a in reversed(ARTICLES[-20:]):
        st.caption(f"{a['published_at']} · {a['source']} · {a['country']}")
        st.markdown(f"**{a['headline']}**")
        st.write(a["url"])
        st.write("---")

# Events
with tabs[3]:
    st.subheader("Upcoming Events")
    now, horizon = datetime.utcnow(), datetime.utcnow() + timedelta(days=1)
    todays = [e for e in EVENTS if now <= e["date_time"] <= horizon]
    if not todays:
        st.info("No upcoming events.")
    for e in todays:
        st.caption(f"{e['date_time']} · {e['country']} · {e['type']}")
        st.write(e["details"])
        st.write("---")

# Ops
with tabs[4]:
    st.subheader("Run logs")
    if not RUNS:
        st.info("No runs yet.")
    for r in reversed(RUNS[-10:]):
        st.write(f"Run {r['run_id']} — started {r['started_at']} (items: {r['items_in']})")
