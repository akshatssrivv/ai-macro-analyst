import streamlit as st
from datetime import datetime, timedelta, timezone
import uuid, requests, feedparser
from bs4 import BeautifulSoup

# In-memory storage (reset each app restart)
RUNS, ARTICLES, EVENTS, BRIEFS = [], [], [], []
UTC = timezone.utc

# ---- source config (public-only; add more later) ----
RSS_SOURCES = [
    # ECB / EU
    ("ECB Press",     "https://www.ecb.europa.eu/press/rss/press.html"),
    ("ECB Speeches",  "https://www.ecb.europa.eu/press/rss/speeches.html"),
    ("ECB Blog",      "https://www.ecb.europa.eu/press/blog/rss/blog.html"),
    ("EU Commission Presscorner", "https://ec.europa.eu/commission/presscorner/home_en?format=RSS"),
    ("Eurostat News", "https://ec.europa.eu/eurostat/news/rss/news-release_en.rss"),

    # National stats offices
    ("INSEE (FR)",    "https://www.insee.fr/en/rss/rss.xml"),
    ("ISTAT (IT)",    "https://www.istat.it/en/feed/"),
    ("Destatis (DE)", "https://www.destatis.de/DE/Service/RSS/english/_node.html"),
    ("INE (ES)",      "https://www.ine.es/info/rss/anu_en.xml"),

    # Debt agencies
    ("AFT (FR)",   "https://www.aft.gouv.fr/en/rss/actualites.xml"),
    ("Finanzagentur (DE)",  "https://www.deutsche-finanzagentur.de/en/rss/press-release-rss-feed/"),
    ("Tesoro (IT)",         "https://www.mef.gov.it/en/rss/rss-news.xml"),
    ("Tesoro Público (ES)", "https://www.tesoro.es/rss"),
]

KEYWORDS = [
    "auction","syndication","issuance","tap","oat","btp","bund","bobls","schatz",
    "gilts","spreads","spread","rating","downgrade","upgrade","fitch","moody","s&p",
    "budget","deficit","debt","ecb","council","lagarde","speech","cut","hike",
    "inflation","cpi","hicp","growth","recession","employment","payroll","strike",
    "industrial","gdp","forecast","syndicate","primary market"
]

def _safe_dt(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=UTC)
    except Exception:
        pass
    return datetime.now(tz=UTC)

def fetch_rss_bulk():
    items = []
    for src_name, url in RSS_SOURCES:
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
            feed = feedparser.parse(r.text)
            for e in feed.entries[:20]:
                title = getattr(e, "title", "") or ""
                summary = getattr(e, "summary", "") or ""
                text = (title + " " + summary).lower()
                if any(k in text for k in KEYWORDS) or "ecb" in text or "euro area" in text:
                    items.append({
                        "source": src_name,
                        "url": getattr(e, "link", ""),
                        "published_at": _safe_dt(e),
                        "country": "EU",
                        "headline": title.strip() or "(no title)",
                        "body": summary,
                    })
        except Exception:
            continue
    items.sort(key=lambda x: x["published_at"], reverse=True)
    return items

def fetch_ecb_calendar_events():
    url = "https://www.ecb.europa.eu/press/rss/speeches.html"
    out = []
    try:
        r = requests.get(url, timeout=10); r.raise_for_status()
        feed = feedparser.parse(r.text)
        for e in feed.entries[:20]:
            dt = _safe_dt(e)
            out.append({
                "date_time": dt,
                "country": "EU",
                "type": "ECB Speech",
                "details": getattr(e, "title", "ECB speech"),
                "source_link": getattr(e, "link", url),
                "status": "upcoming" if dt >= datetime.now(tz=UTC) - timedelta(hours=2) else "released"
            })
    except Exception:
        pass
    horizon = datetime.now(tz=UTC) + timedelta(days=7)
    out = [ev for ev in out if ev["date_time"] <= horizon]
    out.sort(key=lambda x: x["date_time"])
    return out

def run_once():
    run_id = uuid.uuid4().hex[:8]
    started = datetime.now(tz=UTC)
    articles = fetch_rss_bulk()
    events = fetch_ecb_calendar_events()

    top3 = articles[:3]
    brief = {
        "run_id": run_id,
        "created_at": started,
        "what_happened": "; ".join(a["headline"] for a in top3) if top3 else "No new relevant items.",
        "why_it_matters": "Public-source scan across ECB/EU/national stats.",
        "action_bias": "Observe",
        "confidence": 0.4 + 0.2 * (1 if top3 else 0),
        "risks": "Feed gaps; headline-only context.",
        "links": [a["url"] for a in top3 if a.get("url")],
    }

    RUNS.append({"run_id": run_id, "started_at": started, "items_in": len(articles), "items_out": len(events)})
    ARTICLES.extend(articles)
    EVENTS.extend(events)
    BRIEFS.append(brief)

    return {"run_id": run_id, "items_in": len(articles), "items_out": len(events)}

# ------------------ UI ------------------

st.set_page_config(page_title="AI Macro News & Events Analyst", layout="wide")
st.title("AI Macro News & Events Analyst — Demo Skeleton")

# 🔘 Global Run button in sidebar
with st.sidebar:
    st.subheader("Controls")
    if st.button("🔄 Run pipeline now"):
        result = run_once()
        st.success(f"Run {result['run_id']} complete: {result['items_in']} articles, {result['items_out']} events")

tabs = st.tabs(["Briefs", "News Archive", "Events", "Ops"])

# Briefs
with tabs[0]:
    st.subheader("Top items")
    if not BRIEFS:
        st.info("No briefs yet. Hit 'Run pipeline' in sidebar.")
    for b in reversed(BRIEFS[-5:]):
        st.markdown(f"**What**: {b['what_happened']}")
        st.markdown(f"**Why**: {b['why_it_matters']}")
        st.write("---")

# Archive
with tabs[1]:
    st.subheader("News Archive")
    if not ARTICLES:
        st.info("No articles yet.")
    for a in reversed(ARTICLES[-20:]):
        st.caption(f"{a['published_at']} · {a['source']} · {a['country']}")
        st.markdown(f"**{a['headline']}**")
        if a["url"]:
            st.write(f"[Source]({a['url']})")
        st.write("---")

# Events
with tabs[2]:
    st.subheader("Upcoming Events (7 days)")
    now = datetime.now(tz=UTC)
    horizon = now + timedelta(days=7)
    upcoming = [e for e in EVENTS if now - timedelta(hours=2) <= e["date_time"] <= horizon]
    if not upcoming:
        st.info("No events surfaced yet. Run pipeline.")
    for e in sorted(upcoming, key=lambda x: x["date_time"]):
        when = e["date_time"].strftime("%Y-%m-%d %H:%M UTC")
        st.caption(f"{when} · {e['country']} · {e['type']}")
        st.markdown(f"**{e['details']}**")
        if e.get("source_link"):
            st.write(f"[Source]({e['source_link']})")
        st.write("---")

# Ops
with tabs[3]:
    st.subheader("Run logs")
    if not RUNS:
        st.info("No runs yet.")
    for r in reversed(RUNS[-10:]):
        st.write(f"Run {r['run_id']} — started {r['started_at']} (articles: {r['items_in']}, events: {r['items_out']})")
