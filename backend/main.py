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
                        get_news, get_options_open_interest, INDEX_SYMBOLS,
                        screen_stocks, get_sector_performance, get_market_breadth)
from analysis  import analyze_ticker
from models    import Recommendation, WatchlistItem, PortfolioPosition

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

@app.get("/screen/test")
def screen_test():
    """Test endpoint to verify routing works"""
    return {"status": "Screen endpoint is working"}

from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class ScreenRequest(BaseModel):
    min_price: Optional[float] = 1
    max_price: Optional[float] = 1000
    min_volume: Optional[int] = 10000
    min_market_cap: Optional[float] = 10000000  # 10M instead of 100M
    max_market_cap: Optional[float] = None
    patterns: Optional[List[str]] = []

@app.post("/screen")
def screen_endpoint(request: ScreenRequest):
    """Screen stocks based on filters"""
    filters = request.dict(exclude_unset=True)
    
    # Get stocks to screen from major indices
    all_symbols = []
    print("🔍 SCREENING: Fetching index constituents...")
    for idx in ["nasdaq", "sp500"]:
        try:
            print(f"📊 SCREENING: Fetching {idx} constituents...")
            symbols = get_constituents(idx)
            all_symbols += symbols
            print(f"✅ SCREENING: Got {len(symbols)} symbols from {idx}")
        except Exception as e:
            print(f"❌ SCREENING: Failed to get {idx} constituents: {e}")
    
    # If we couldn't get index constituents, use a fallback list
    if not all_symbols:
        print("⚠️ SCREENING: No index data available, using fallback stock list")
        all_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "AVGO", "JPM",
            "JNJ", "V", "PG", "UNH", "HD", "MA", "PFE", "BAC", "ABBV", "CRM",
            "KO", "TMO", "COST", "PEP", "WMT", "DIS", "ABT", "MRK", "VZ", "ADBE",
            "NFLX", "AMD", "INTC", "IBM", "ORCL", "COP", "T", "CVX", "XOM", "WFC",
            "IMNN", "COIN", "PLTR", "RBLX", "RIVN", "LCID", "SOFI", "HOOD", "AMC", "GME"
        ]
        print(f"📋 SCREENING: Using {len(all_symbols)} fallback symbols")
    else:
        all_symbols = list(set(all_symbols))
        print(f"📊 SCREENING: Total unique symbols to screen: {len(all_symbols)}")
    
    results = screen_stocks(all_symbols, filters)
    return {"screener_results": results}

@app.get("/market/sectors")
def market_sectors():
    """Get sector performance analysis"""
    return {"sector_performance": get_sector_performance()}

@app.get("/market/breadth")  
def market_breadth():
    """Get market breadth indicators"""
    return {"market_breadth": get_market_breadth()}

@app.get("/market/context")
def market_context():
    """Get comprehensive market context"""
    breadth = get_market_breadth()
    sectors = get_sector_performance()
    
    # Determine market regime
    regime_signals = []
    if breadth.get("spy_vs_sma20", 0) > 0:
        regime_signals.append("SPY above 20-day SMA")
    if breadth.get("vix", 30) < 20:
        regime_signals.append("Low volatility (VIX < 20)")
    
    # Count sectors in uptrend (positive 20-day performance)
    sectors_up = sum(1 for s in sectors.values() if s.get("performance_20d", 0) > 0)
    total_sectors = len(sectors)
    
    if sectors_up / total_sectors > 0.6:
        regime_signals.append("Sector breadth positive")
    
    market_regime = "BULL_TREND" if len(regime_signals) >= 2 else "UNCERTAIN"
    
    return {
        "market_context": {
            "regime": market_regime,
            "regime_signals": regime_signals,
            "breadth": breadth,
            "sector_performance": sectors,
            "sectors_advancing": f"{sectors_up}/{total_sectors}"
        }
    }

class PositionRequest(BaseModel):
    symbol: str
    entry_date: str
    entry_price: float
    quantity: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    notes: Optional[str] = ""

class PositionUpdateRequest(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: Optional[str] = None
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    notes: Optional[str] = None

# Portfolio Management Endpoints
@app.post("/portfolio/positions")
def add_position(request: PositionRequest):
    """Add a new portfolio position"""
    position = PortfolioPosition(
        symbol=request.symbol.upper(),
        entry_date=date.fromisoformat(request.entry_date),
        entry_price=request.entry_price,
        quantity=request.quantity,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        notes=request.notes or ""
    )
    
    with Session(engine) as sess:
        sess.add(position)
        sess.commit()
        sess.refresh(position)
    
    return {"message": "Position added successfully", "position_id": position.id}

@app.get("/portfolio/positions")
def get_positions():
    """Get all portfolio positions with current performance"""
    with Session(engine) as sess:
        positions = sess.exec(select(PortfolioPosition)).all()
    
    # Enrich positions with current market data
    enriched_positions = []
    for pos in positions:
        try:
            df = fetch_ohlcv(pos.symbol, months=1)
            if not df.empty:
                current_price = df["Close"].iloc[-1]
                unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
                unrealized_pnl_pct = ((current_price / pos.entry_price) - 1) * 100
                
                position_dict = {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "entry_date": pos.entry_date.isoformat(),
                    "entry_price": pos.entry_price,
                    "current_price": round(current_price, 2),
                    "quantity": pos.quantity,
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                    "status": pos.status,
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                    "position_value": round(current_price * pos.quantity, 2),
                    "cost_basis": round(pos.entry_price * pos.quantity, 2),
                    "notes": pos.notes
                }
                enriched_positions.append(position_dict)
        except:
            # If we can't get current price, use entry price
            position_dict = {
                "id": pos.id,
                "symbol": pos.symbol,
                "entry_date": pos.entry_date.isoformat(),
                "entry_price": pos.entry_price,
                "current_price": pos.entry_price,
                "quantity": pos.quantity,
                "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit,
                "status": pos.status,
                "unrealized_pnl": 0,
                "unrealized_pnl_pct": 0,
                "position_value": pos.entry_price * pos.quantity,
                "cost_basis": pos.entry_price * pos.quantity,
                "notes": pos.notes
            }
            enriched_positions.append(position_dict)
    
    return {"positions": enriched_positions}

@app.put("/portfolio/positions/{position_id}")
def update_position(position_id: int, request: PositionUpdateRequest):
    """Update a portfolio position"""
    with Session(engine) as sess:
        position = sess.get(PortfolioPosition, position_id)
        if not position:
            raise HTTPException(404, "Position not found")
        
        # Update fields if provided
        if request.stop_loss is not None:
            position.stop_loss = request.stop_loss
        if request.take_profit is not None:
            position.take_profit = request.take_profit
        if request.status is not None:
            position.status = request.status
        if request.exit_date is not None:
            position.exit_date = date.fromisoformat(request.exit_date)
        if request.exit_price is not None:
            position.exit_price = request.exit_price
        if request.notes is not None:
            position.notes = request.notes
        
        sess.commit()
    
    return {"message": "Position updated successfully"}

@app.delete("/portfolio/positions/{position_id}")
def delete_position(position_id: int):
    """Delete a portfolio position"""
    with Session(engine) as sess:
        position = sess.get(PortfolioPosition, position_id)
        if not position:
            raise HTTPException(404, "Position not found")
        
        sess.delete(position)
        sess.commit()
    
    return {"message": "Position deleted successfully"}

@app.get("/portfolio/performance")
def get_portfolio_performance():
    """Get overall portfolio performance metrics"""
    with Session(engine) as sess:
        positions = sess.exec(select(PortfolioPosition)).all()
    
    total_cost_basis = 0
    total_current_value = 0
    total_realized_pnl = 0
    open_positions = 0
    closed_positions = 0
    
    for pos in positions:
        cost_basis = pos.entry_price * pos.quantity
        total_cost_basis += cost_basis
        
        if pos.status == "OPEN":
            open_positions += 1
            try:
                df = fetch_ohlcv(pos.symbol, months=1)
                if not df.empty:
                    current_price = df["Close"].iloc[-1]
                    total_current_value += current_price * pos.quantity
            except:
                total_current_value += cost_basis
        else:
            closed_positions += 1
            if pos.exit_price:
                realized_pnl = (pos.exit_price - pos.entry_price) * pos.quantity
                total_realized_pnl += realized_pnl
    
    total_unrealized_pnl = total_current_value - total_cost_basis
    total_pnl = total_realized_pnl + total_unrealized_pnl
    total_return_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    return {
        "portfolio_performance": {
            "total_positions": len(positions),
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "total_cost_basis": round(total_cost_basis, 2),
            "total_current_value": round(total_current_value, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2)
        }
    }
