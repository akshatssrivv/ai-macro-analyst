import streamlit as st
from datetime import datetime, timedelta, timezone
import uuid, requests, feedparser
from bs4 import BeautifulSoup

# In-memory storage (reset each app restart)
RUNS, ARTICLES, EVENTS, BRIEFS = [], [], [], []
UTC = timezone.utc

# ---- source config (RSS still included) ----
RSS_SOURCES = [
    # ECB / EU institutions
    ("ECB Press", "https://www.ecb.europa.eu/press/rss/press.html"),
    ("ECB Speeches", "https://www.ecb.europa.eu/press/rss/speeches.html"),
    ("ECB Blog", "https://www.ecb.europa.eu/press/blog/rss/blog.html"),
    ("EU Commission Presscorner", "https://ec.europa.eu/commission/presscorner/home_en?format=RSS"),
    ("Eurostat News", "https://ec.europa.eu/eurostat/news/rss/news-release_en.rss"),

    # National stats offices
    ("INSEE (FR)", "https://www.insee.fr/en/rss/rss.xml"),
    ("ISTAT (IT)", "https://www.istat.it/en/feed/"),
    ("Destatis (DE)", "https://www.destatis.de/DE/Service/RSS/english/_node.html"),
    ("INE (ES)", "https://www.ine.es/info/rss/anu_en.xml"),

    # Debt agencies
    ("AFT (FR)", "https://www.aft.gouv.fr/en/rss/actualites.xml"),
    ("Finanzagentur (DE)", "https://www.deutsche-finanzagentur.de/en/rss/press-release-rss-feed/"),
    ("Tesoro (IT)", "https://www.mef.gov.it/en/rss/rss-news.xml"),
    ("Tesoro Público (ES)", "https://www.tesoro.es/rss"),

    # Global wires
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets", "https://feeds.reuters.com/reuters/marketsNews"),
    ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
    ("AP Top News", "https://apnews.com/hub/ap-top-news?format=xml"),
    ("AP Business", "https://apnews.com/hub/business?format=xml"),

    # European press
    ("Handelsblatt (DE)", "https://www.handelsblatt.com/contentexport/feed/rss/finanzen"),
    ("Les Échos (FR)", "https://www.lesechos.fr/rss/rss_finances.xml"),
    ("Expansión (ES)", "https://e00-expansion.uecdn.es/rss/mercados.xml"),
    ("Il Sole 24 Ore (IT)", "https://www.ilsole24ore.com/rss/finanza.xml"),
    ("ANSA Economy (IT)", "https://www.ansa.it/sito/notizie/economia/economia_rss.xml"),

    # EU politics
    ("Politico Europe", "https://www.politico.eu/feed/"),
    ("Euractiv", "https://www.euractiv.com/feed/"),

    # Think tanks
    ("Bruegel", "https://www.bruegel.org/rss.xml"),

    # Ratings agencies
    ("Fitch Ratings", "https://www.fitchratings.com/site/rss"),
]



KEYWORDS = [
    "auction","syndication","issuance","tap","oat","btp","bund","bobls","schatz",
    "gilts","spread","rating","downgrade","upgrade","fitch","moody","s&p",
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

# ---- collectors ----
def fetch_gdelt_news():
    """
    Enhanced GDELT collector:
    - Multiple queries (themes + free text)
    - 72h window
    - Dedup by URL
    """
    queries = [
        "theme:SOVEREIGN_DEBT",
        "theme:INFLATION",
        "theme:INTEREST_RATES",
        "theme:ECON_FINANCE",
        "ECB OR Eurozone OR OAT OR Bund OR BTP OR Gilts OR Treasuries OR sovereign bond"
    ]

    now = datetime.utcnow()
    since = now - timedelta(days=3)   # 72h window
    start = since.strftime("%Y%m%d%H%M%S")
    end = now.strftime("%Y%m%d%H%M%S")

    all_items = []
    seen_urls = set()

    for q in queries:
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={q}&mode=ArtList&startdatetime={start}&enddatetime={end}"
            "&maxrecords=250&format=json"
        )
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            for item in data.get("articles", []):
                u = item.get("url")
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)
                try:
                    dt = datetime.strptime(item["seendate"], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
                except Exception:
                    dt = datetime.now(tz=UTC)
                all_items.append({
                    "source": f"GDELT ({q})",
                    "url": u,
                    "published_at": dt,
                    "country": item.get("sourceCountry", "N/A"),
                    "headline": item.get("title", "(no title)"),
                    "body": item.get("url")  # no summary, keep URL as placeholder
                })
        except Exception as e:
            print(f"GDELT fetch failed for query {q}:", e)

    # sort newest first
    all_items.sort(key=lambda x: x["published_at"], reverse=True)
    return all_items

    
def fetch_rss_bulk():
    items = []
    for src_name, url in RSS_SOURCES:
        try:
            r = requests.get(url, timeout=10); r.raise_for_status()
            feed = feedparser.parse(r.text)
            for e in feed.entries[:20]:
                title = getattr(e, "title", "") or ""
                summary = getattr(e, "summary", "") or ""
                dt = _safe_dt(e)
                items.append({
                    "source": src_name,
                    "url": getattr(e, "link", ""),
                    "published_at": dt,
                    "country": "EU",
                    "headline": title.strip() or "(no title)",
                    "body": summary,
                })
        except Exception as ex:
            print(f"RSS failed for {src_name}: {ex}")
    items.sort(key=lambda x: x["published_at"], reverse=True)
    return items


def fetch_eurostat_news():
    url = "https://ec.europa.eu/eurostat/api/dissemination/news"
    items = []
    try:
        data = requests.get(url, timeout=10).json()
        print("Eurostat items:", len(data.get("value", [])))
        for item in data.get("value", [])[:10]:
            dt = datetime.fromisoformat(item["date"]).replace(tzinfo=UTC)
            items.append({
                "source": "Eurostat",
                "url": item.get("link"),
                "published_at": dt,
                "country": "EU",
                "headline": item.get("title"),
                "body": item.get("summary", "")
            })
    except Exception as e:
        print("Eurostat fetch failed", e)
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

def fetch_aft_calendar():
    """Scrape French AFT auction calendar."""
    url = "https://www.aft.gouv.fr/en/archives/calendar"
    events = []
    try:
        r = requests.get(url, timeout=10); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("table tbody tr"):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 2:
                date_str, details = cols[0], cols[1]
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=UTC)
                except Exception:
                    continue
                events.append({
                    "date_time": dt,
                    "country": "FR",
                    "type": "Auction",
                    "details": details,
                    "source_link": url,
                    "status": "upcoming" if dt > datetime.now(tz=UTC) else "released"
                })
    except Exception as e:
        print("AFT scrape failed", e)
    return events

# ---- pipeline ----
def run_once():
    run_id = uuid.uuid4().hex[:8]
    started = datetime.now(tz=UTC)

    # pull fresh
    rss_articles = fetch_rss_bulk()
    gdelt_articles = fetch_gdelt_news()
    all_articles = rss_articles + gdelt_articles

    # global dedup by URL
    seen = {a["url"] for a in ARTICLES}
    new_articles = [a for a in all_articles if a["url"] not in seen]

    # pull events
    events = fetch_ecb_calendar_events() + fetch_aft_calendar()

    # brief from top 3 new articles
    top3 = new_articles[:3]
    brief = {
        "run_id": run_id,
        "created_at": started,
        "what_happened": "; ".join(a["headline"] for a in top3) if top3 else "No new relevant items.",
        "why_it_matters": "Mixed-source scan: RSS + GDELT + calendars.",
        "action_bias": "Observe",
        "confidence": 0.4 + 0.2 * (1 if top3 else 0),
        "risks": "Feed gaps; headline-only context.",
        "links": [a["url"] for a in top3 if a.get("url")],
    }

    # persist
    RUNS.append({
        "run_id": run_id,
        "started_at": started,
        "items_in": len(all_articles),
        "items_new": len(new_articles),
        "items_out": len(events)
    })
    ARTICLES.extend(new_articles)
    EVENTS.extend(events)
    BRIEFS.append(brief)

    return {
        "run_id": run_id,
        "items_in": len(all_articles),
        "items_new": len(new_articles),
        "items_out": len(events)
    }


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
        st.info("No briefs yet. Run pipeline from sidebar.")
    for b in reversed(BRIEFS[-5:]):
        st.markdown(f"**What**: {b['what_happened']}")
        st.markdown(f"**Why**: {b['why_it_matters']}")
        st.write("---")

# Archive
with tabs[1]:
    st.subheader("News Archive")

    if not ARTICLES:
        st.info("No articles yet.")
    else:
        # --- sort order control ---
        sort_order = st.radio(
            "Sort by",
            ["Newest first", "Oldest first"],
            horizontal=True,
            index=0
        )

        sorted_articles = sorted(
            ARTICLES,
            key=lambda x: x["published_at"],
            reverse=(sort_order == "Newest first")
        )

        # --- pagination ---
        per_page = 10
        total = len(sorted_articles)
        total_pages = (total + per_page - 1) // per_page

        # pick page
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1
        )

        start = (page - 1) * per_page
        end = start + per_page
        page_articles = sorted_articles[start:end]

        st.caption(f"Showing {len(page_articles)} of {total} articles")

        for a in page_articles:
            st.caption(f"{a['published_at']} · {a['source']} · {a['country']}")
            st.markdown(f"**{a['headline']}**")
            if a["url"]:
                st.write(f"[Source]({a['url']})")
            st.write("---")

        # page nav
        st.write(f"Page {page} of {total_pages}")


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


