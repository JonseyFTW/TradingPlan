import os
import json
from datetime import date
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Session, create_engine, select
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from utils     import (get_constituents, get_fundamentals,
                        get_earnings, get_earnings_calendar,
                        get_news, get_options_open_interest, INDEX_SYMBOLS)
from analysis  import analyze_ticker
from models    import Recommendation, WatchlistItem

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

scheduler = BackgroundScheduler()
CRON = os.getenv("SCAN_CRON", "0 6 * * *").split()

def run_recommendations():
    today = date.today()
    all_syms = []
    for idx in ["nasdaq","sp500","dow"]:
        try:
            all_syms += get_constituents(idx)
        except:
            pass
    analyses = []
    for s in set(all_syms):
        r = analyze_ticker(s)
        if "error" not in r and r["score"]>0:
            analyses.append(r)
    # rank top 20
    top = sorted(analyses, key=lambda x: x["score"], reverse=True)[:20]
    with Session(engine) as sess:
        # delete old for today
        old_recs = sess.exec(select(Recommendation).where(Recommendation.date==today)).all()
        for rec in old_recs:
            sess.delete(rec)
        for a in top:
            rec = Recommendation(
              date=today,
              symbol=a["symbol"],
              score=a["score"],
              analysis_data=json.dumps(a)
            )
            sess.add(rec)
        sess.commit()
    print(f"🗓️ Recommendations for {today} saved.")

def parse_cron_field(field):
    return None if field == '*' else int(field)

scheduler.add_job(
    run_recommendations, 'cron',
    minute=parse_cron_field(CRON[0]),
    hour=parse_cron_field(CRON[1]),
    day=parse_cron_field(CRON[2]),
    month=parse_cron_field(CRON[3]),
    day_of_week=None if CRON[4] == '*' else CRON[4]
)
scheduler.start()

@app.get("/indices")
def list_indices():
    return {"available": list(INDEX_SYMBOLS.keys())}

@app.get("/analyze/{symbol}")
def analyze(symbol: str):
    r = analyze_ticker(symbol.upper())
    if "error" in r:
        raise HTTPException(404, r["error"])
    return r

@app.get("/scan/{index_name}")
def scan_index(index_name: str):
    try:
        syms = get_constituents(index_name)
    except:
        raise HTTPException(404, "Index not found")
    candidates = []
    for s in syms:
        r = analyze_ticker(s)
        if "error" not in r and r["score"]>0:
            candidates.append(r)
    return {"candidates": candidates}

@app.get("/recommendations")
def recommendations():
    today = date.today()
    with Session(engine) as sess:
        recs = sess.exec(
          select(Recommendation).where(Recommendation.date==today)
        ).all()
    return {"recommendations": [json.loads(r.analysis_data) for r in recs]}

@app.get("/recommendations/history")
def rec_history():
    with Session(engine) as sess:
        recs = sess.exec(select(Recommendation)).all()
    return {"history": recs}

@app.get("/fundamentals/{symbol}")
def fundamentals(symbol: str):
    return get_fundamentals(symbol.upper())

@app.get("/earnings/{symbol}")
def earnings(symbol: str):
    return get_earnings(symbol.upper())

@app.get("/earnings/calendar")
def earnings_calendar():
    return get_earnings_calendar()

@app.get("/news/{symbol}")
def news(symbol: str):
    return get_news(symbol.upper())

@app.get("/options/{symbol}/open_interest")
def options_oi(symbol: str):
    return get_options_open_interest(symbol.upper())

@app.post("/watchlist/{symbol}")
def add_watch(symbol: str):
    item = WatchlistItem(symbol=symbol.upper())
    with Session(engine) as sess:
        sess.add(item); sess.commit()
    return {"added": symbol.upper()}

@app.get("/watchlist")
def get_watch():
    with Session(engine) as sess:
        items = sess.exec(select(WatchlistItem)).all()
    return {"watchlist": [i.symbol for i in items]}

@app.delete("/watchlist/{symbol}")
def del_watch(symbol: str):
    with Session(engine) as sess:
        item = sess.get(WatchlistItem, symbol.upper())
        if not item:
            raise HTTPException(404, "Not in watchlist")
        sess.delete(item); sess.commit()
    return {"deleted": symbol.upper()}

@app.get("/alerts/latest")
def alerts_latest():
    # alias for today's recommendations
    return recommendations()
