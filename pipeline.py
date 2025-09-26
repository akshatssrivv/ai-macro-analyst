import uuid
from datetime import datetime, timedelta
from loguru import logger
from db import get_collection

def run_once():
    run_id = uuid.uuid4().hex[:12]
    started = datetime.utcnow()

    # dummy collect
    articles = [
        {"source": "DUMMY", "url": "https://example.com/eu-budget", "published_at": started,
         "country": "EU", "headline": "EU budget talks progress (dummy)"},
        {"source": "DUMMY", "url": "https://example.com/aft-auction", "published_at": started,
         "country": "FR", "headline": "AFT schedules OAT auction (dummy)"},
    ]
    events = [
        {"date_time": started + timedelta(hours=2), "country": "US", "type": "macro release",
         "details": "NFP at 13:30 UK (dummy)", "source_link": "https://www.bls.gov/", "status": "upcoming"}
    ]

    news_col = get_collection("news_article")
    ev_col = get_collection("calendar_event")
    brief_col = get_collection("brief_item")
    run_log = get_collection("run_log")

    news_ids = news_col.insert_many(articles).inserted_ids
    ev_col.insert_many(events)

    brief_col.insert_one({
        "run_id": run_id,
        "created_at": started,
        "article_ids": news_ids,
        "what_happened": "; ".join(a["headline"] for a in articles),
        "why_it_matters": "Scaffold test with MongoDB: verifies end-to-end wiring.",
        "action_bias": "Observe",
        "confidence": 0.5,
        "risks": "None",
        "links": [a["url"] for a in articles],
    })

    finished = datetime.utcnow()
    run_log.insert_one({
        "run_id": run_id,
        "started_at": started,
        "finished_at": finished,
        "items_in": len(articles),
        "items_out": len(articles),
        "latency_ms": int((finished - started).total_seconds() * 1000),
    })

    logger.info(f"Run {run_id} stored in Mongo")
    return {"run_id": run_id, "items_in": len(articles), "items_out": len(articles)}

