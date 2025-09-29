import streamlit as st
from datetime import datetime, timedelta
from db import get_collection
from pipeline import run_once

st.sidebar.success("✅ Connected to MongoDB")

st.set_page_config(page_title="AI Macro News & Events Analyst", layout="wide")
st.title("AI Macro News & Events Analyst — Mongo Skeleton")

tabs = st.tabs(["Briefs", "Run Now", "News Archive", "Events", "Ops"])

# Briefs
with tabs[0]:
    st.subheader("Top items (latest first)")
    briefs = list(get_collection("brief_item").find().sort("created_at", -1).limit(5))
    if not briefs:
        st.info("No briefs yet. Use the Run Now tab.")
    for b in briefs:
        st.markdown(f"**What**: {b.get('what_happened','')}")
        st.markdown(f"**Why**: {b.get('why_it_matters','')}")
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
    articles = list(get_collection("news_article").find().sort("published_at", -1).limit(20))
    for a in articles:
        st.caption(f"{a.get('published_at')} · {a.get('source')} · {a.get('country')}")
        st.markdown(f"**{a.get('headline','')}**")
        st.write(a.get("url",""))
        st.write("---")

# Events
with tabs[3]:
    st.subheader("Upcoming Events")
    now, horizon = datetime.utcnow(), datetime.utcnow() + timedelta(days=1)
    events = list(get_collection("calendar_event")
                  .find({"date_time": {"$gte": now, "$lte": horizon}})
                  .sort("date_time", 1))
    for e in events:
        st.caption(f"{e.get('date_time')} · {e.get('country')} · {e.get('type')}")
        st.write(e.get("details",""))
        st.write("---")

# Ops
with tabs[4]:
    st.subheader("Run logs")
    logs = list(get_collection("run_log").find().sort("started_at", -1).limit(10))
    for r in logs:
        st.write(f"Run {r.get('run_id')} — {r.get('started_at')} → {r.get('finished_at')}")

