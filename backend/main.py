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
from models    import Recommendation, WatchlistItem, PortfolioPosition, ScreenerCache, TradingPlan

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

def run_daily_screening():
    """Pre-cache common screening patterns at 1am daily"""
    print(f"🕐 Starting daily pre-screening at 1am...")
    today = date.today()
    
    # Get all symbols for screening
    all_symbols = []
    for idx in ["nasdaq", "sp500", "dow", "iwm"]:
        try:
            symbols = get_constituents(idx)
            all_symbols += symbols
        except:
            pass
    
    all_symbols = list(set(all_symbols))
    print(f"📊 PRE-SCREENING: Processing {len(all_symbols)} symbols for common patterns")
    
    # Common filter combinations to pre-cache
    common_filters = [
        # Default filters (most common usage)
        {
            "min_price": 1,
            "max_price": 1000,
            "min_volume": 10000,
            "min_market_cap": 10000000,
            "patterns": []
        },
        # Popular pattern combinations
        {
            "min_price": 5,
            "max_price": 500,
            "min_volume": 100000,
            "min_market_cap": 50000000,
            "patterns": ["momentum"]
        },
        {
            "min_price": 10,
            "max_price": 200,
            "min_volume": 100000,
            "min_market_cap": 100000000,
            "patterns": ["breakout"]
        },
        {
            "min_price": 5,
            "max_price": 500,
            "min_volume": 100000,
            "min_market_cap": 50000000,
            "patterns": ["oversold_bounce"]
        },
        {
            "min_price": 10,
            "max_price": 300,
            "min_volume": 100000,
            "min_market_cap": 100000000,
            "patterns": ["momentum", "breakout"]
        }
    ]
    
    with Session(engine) as sess:
        # Clear old cache entries first
        old_cache = sess.exec(
            select(ScreenerCache).where(ScreenerCache.created_date < today)
        ).all()
        for cache in old_cache:
            sess.delete(cache)
        sess.commit()
        print(f"🗑️ PRE-SCREENING: Cleared {len(old_cache)} old cache entries")
    
    # Pre-cache each filter combination
    for i, filters in enumerate(common_filters, 1):
        try:
            print(f"🔍 PRE-SCREENING: Running filter set {i}/{len(common_filters)}")
            
            # Generate cache key
            cache_key = ScreenerCache.generate_cache_key(filters)
            
            # Check if already cached today
            with Session(engine) as sess:
                existing = sess.exec(
                    select(ScreenerCache).where(
                        ScreenerCache.cache_key == cache_key,
                        ScreenerCache.created_date == today
                    )
                ).first()
                
                if existing:
                    print(f"✅ PRE-SCREENING: Filter set {i} already cached")
                    continue
            
            # Run screening
            results = screen_stocks(all_symbols, filters)
            
            # Cache the results
            with Session(engine) as sess:
                cache_entry = ScreenerCache(
                    cache_key=cache_key,
                    filters_json=json.dumps(filters),
                    results_json=json.dumps(results),
                    created_date=today,
                    result_count=len(results)
                )
                sess.add(cache_entry)
                sess.commit()
                print(f"💾 PRE-SCREENING: Cached {len(results)} results for filter set {i}")
                
        except Exception as e:
            print(f"❌ PRE-SCREENING: Failed filter set {i}: {e}")
    
    print(f"🎉 Daily pre-screening completed!")

def parse_cron_field(field):
    return None if field == '*' else int(field)

# Add recommendation job
scheduler.add_job(
    run_recommendations, 'cron',
    minute=parse_cron_field(CRON[0]),
    hour=parse_cron_field(CRON[1]),
    day=parse_cron_field(CRON[2]),
    month=parse_cron_field(CRON[3]),
    day_of_week=None if CRON[4] == '*' else CRON[4]
)

# Add daily pre-screening job at 1am
scheduler.add_job(
    run_daily_screening, 'cron',
    minute=0,
    hour=1,  # 1am daily
    day='*',
    month='*',
    day_of_week='*'
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
    """Screen stocks based on filters with caching"""
    filters = request.dict(exclude_unset=True)
    today = date.today()
    
    # Generate cache key for this filter combination
    cache_key = ScreenerCache.generate_cache_key(filters)
    
    # Check if we have cached results from today
    with Session(engine) as sess:
        cached_result = sess.exec(
            select(ScreenerCache).where(
                ScreenerCache.cache_key == cache_key,
                ScreenerCache.created_date == today
            )
        ).first()
        
        if cached_result:
            print(f"🚀 SCREENING: Using cached results for today ({cached_result.result_count} stocks)")
            cached_data = json.loads(cached_result.results_json)
            return {
                "screener_results": cached_data,
                "from_cache": True,
                "cache_date": cached_result.created_date.isoformat()
            }
    
    # No cache found - run fresh screening
    print(f"🔍 SCREENING: No cache found, running fresh screen...")
    
    # Get stocks to screen from major indices
    all_symbols = []
    print("🔍 SCREENING: Fetching index constituents...")
    for idx in ["nasdaq", "sp500", "dow", "iwm"]:
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
    
    # Run the screening
    results = screen_stocks(all_symbols, filters)
    
    # Cache the results
    try:
        with Session(engine) as sess:
            # Remove any old cache entries for this filter combination
            old_cache = sess.exec(
                select(ScreenerCache).where(ScreenerCache.cache_key == cache_key)
            ).all()
            for old in old_cache:
                sess.delete(old)
            
            # Create new cache entry
            cache_entry = ScreenerCache(
                cache_key=cache_key,
                filters_json=json.dumps(filters),
                results_json=json.dumps(results),
                created_date=today,
                result_count=len(results)
            )
            sess.add(cache_entry)
            sess.commit()
            print(f"💾 SCREENING: Cached {len(results)} results for future use")
    except Exception as e:
        print(f"⚠️ SCREENING: Failed to cache results: {e}")
    
    return {
        "screener_results": results,
        "from_cache": False,
        "cache_date": today.isoformat()
    }

@app.get("/screen/cache")
def get_cached_screens():
    """Get all cached screening results for today"""
    today = date.today()
    with Session(engine) as sess:
        cached_results = sess.exec(
            select(ScreenerCache).where(ScreenerCache.created_date == today)
        ).all()
        
        cache_info = []
        for cache in cached_results:
            filters = json.loads(cache.filters_json)
            cache_info.append({
                "cache_key": cache.cache_key,
                "filters": filters,
                "result_count": cache.result_count,
                "created_date": cache.created_date.isoformat()
            })
        
        return {"cached_screens": cache_info}

@app.delete("/screen/cache")
def clear_screen_cache():
    """Clear all cached screening results"""
    with Session(engine) as sess:
        old_cache = sess.exec(select(ScreenerCache)).all()
        for cache in old_cache:
            sess.delete(cache)
        sess.commit()
        return {"message": f"Cleared {len(old_cache)} cached screening results"}

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

# Plan Builder Endpoints

class PlanBuilderRequest(BaseModel):
    plan_name: str
    total_capital: float
    risk_percentage: float = 2.0
    max_positions: int = 5
    filters: dict
    
@app.post("/plan-builder/create")
def create_trading_plan(request: PlanBuilderRequest):
    """Create a comprehensive trading plan with position sizing and allocation"""
    today = date.today()
    
    # Validate inputs
    if request.total_capital <= 0:
        raise HTTPException(400, "Total capital must be positive")
    if request.risk_percentage <= 0 or request.risk_percentage > 10:
        raise HTTPException(400, "Risk percentage must be between 0.1% and 10%")
    if request.max_positions < 1 or request.max_positions > 20:
        raise HTTPException(400, "Max positions must be between 1 and 20")
    
    # Get screening results (try cache first)
    cache_key = ScreenerCache.generate_cache_key(request.filters)
    screening_results = []
    
    with Session(engine) as sess:
        # Try to get cached results first
        cached_result = sess.exec(
            select(ScreenerCache).where(
                ScreenerCache.cache_key == cache_key,
                ScreenerCache.created_date == today
            )
        ).first()
        
        if cached_result:
            print(f"🚀 PLAN BUILDER: Using cached screening results")
            screening_results = json.loads(cached_result.results_json)
        else:
            print(f"🔍 PLAN BUILDER: Running fresh screening for plan")
            # Get symbols and run screening
            all_symbols = []
            for idx in ["nasdaq", "sp500", "dow", "iwm"]:
                try:
                    symbols = get_constituents(idx)
                    all_symbols += symbols
                except:
                    pass
            
            all_symbols = list(set(all_symbols))
            screening_results = screen_stocks(all_symbols, request.filters)
    
    # Sort by score and take top candidates
    top_candidates = sorted(screening_results, key=lambda x: x.get("score", 0), reverse=True)
    
    # Select top stocks for the plan (up to max_positions)
    selected_stocks = top_candidates[:request.max_positions]
    
    if not selected_stocks:
        raise HTTPException(404, "No stocks found matching the criteria")
    
    # Create detailed trading plan for each stock
    plan_positions = []
    total_allocated = 0
    
    for stock in selected_stocks:
        try:
            # Get detailed analysis for entry/exit planning
            analysis = analyze_ticker(stock["symbol"])
            if "error" in analysis:
                continue
                
            current_price = stock["price"]
            
            # Calculate position sizing based on plan analysis
            plan_entry_range = analysis.get("plan", {}).get("entry", [current_price])
            suggested_entry = plan_entry_range[0] if plan_entry_range else current_price
            suggested_stop = analysis.get("plan", {}).get("stop_loss", current_price * 0.92)  # 8% default stop
            
            # Calculate position size using risk management
            position_info = TradingPlan.calculate_position_sizing(
                request.total_capital / request.max_positions,  # Equal allocation base
                request.risk_percentage,
                suggested_entry,
                suggested_stop
            )
            
            if position_info["shares"] == 0:
                continue
                
            # Get targets from analysis
            targets = analysis.get("plan", {}).get("targets", [
                {"price": current_price * 1.10, "pct": 50},
                {"price": current_price * 1.20, "pct": 30},
                {"price": current_price * 1.30, "pct": 20}
            ])
            
            position_plan = {
                "symbol": stock["symbol"],
                "current_price": current_price,
                "score": stock.get("score", 0),
                "patterns": stock.get("patterns", []),
                "sector": stock.get("sector", "Unknown"),
                
                # Entry strategy
                "suggested_entry": round(suggested_entry, 2),
                "entry_range": [round(p, 2) for p in plan_entry_range[:2]] if len(plan_entry_range) >= 2 else [round(suggested_entry, 2)],
                
                # Position sizing
                "shares": position_info["shares"],
                "position_value": position_info["position_value"],
                "allocation_pct": round((position_info["position_value"] / request.total_capital) * 100, 1),
                
                # Risk management
                "stop_loss": round(suggested_stop, 2),
                "risk_amount": position_info["risk_amount"],
                "risk_pct": round((position_info["risk_amount"] / request.total_capital) * 100, 2),
                
                # Profit targets
                "targets": [
                    {
                        "price": round(target["price"], 2),
                        "shares_to_sell": int(position_info["shares"] * target["pct"] / 100),
                        "allocation_pct": target["pct"],
                        "potential_profit": round((target["price"] - suggested_entry) * int(position_info["shares"] * target["pct"] / 100), 2)
                    }
                    for target in targets
                ],
                
                # Technical levels
                "support_level": analysis.get("summary", {}).get("key_levels", {}).get("support", suggested_stop),
                "resistance_level": analysis.get("summary", {}).get("key_levels", {}).get("resistance", current_price * 1.15),
                
                # Analysis summary
                "conviction": analysis.get("summary", {}).get("conviction", "MEDIUM"),
                "recommendation": analysis.get("summary", {}).get("recommendation", "Hold for technical setup")
            }
            
            plan_positions.append(position_plan)
            total_allocated += position_info["position_value"]
            
        except Exception as e:
            print(f"⚠️ PLAN BUILDER: Error processing {stock['symbol']}: {e}")
            continue
    
    if not plan_positions:
        raise HTTPException(404, "Unable to create positions for any selected stocks")
    
    # Create plan summary
    plan_summary = {
        "plan_name": request.plan_name,
        "created_date": today.isoformat(),
        "capital_info": {
            "total_capital": request.total_capital,
            "allocated_capital": round(total_allocated, 2),
            "cash_remaining": round(request.total_capital - total_allocated, 2),
            "allocation_pct": round((total_allocated / request.total_capital) * 100, 1)
        },
        "risk_management": {
            "risk_per_position": request.risk_percentage,
            "max_positions": request.max_positions,
            "total_risk_amount": round(sum(pos["risk_amount"] for pos in plan_positions), 2),
            "total_risk_pct": round(sum(pos["risk_pct"] for pos in plan_positions), 2)
        },
        "positions": plan_positions,
        "screening_info": {
            "total_candidates": len(screening_results),
            "selected_positions": len(plan_positions),
            "filters_used": request.filters
        }
    }
    
    # Save plan to database
    try:
        with Session(engine) as sess:
            trading_plan = TradingPlan(
                plan_name=request.plan_name,
                total_capital=request.total_capital,
                risk_percentage=request.risk_percentage,
                max_positions=request.max_positions,
                filters_json=json.dumps(request.filters),
                created_date=today,
                plan_data=json.dumps(plan_summary)
            )
            sess.add(trading_plan)
            sess.commit()
            sess.refresh(trading_plan)
            
            plan_summary["plan_id"] = trading_plan.id
            print(f"💾 PLAN BUILDER: Saved plan '{request.plan_name}' with {len(plan_positions)} positions")
            
    except Exception as e:
        print(f"⚠️ PLAN BUILDER: Failed to save plan: {e}")
        # Still return the plan even if saving fails
        plan_summary["plan_id"] = None
    
    return {"trading_plan": plan_summary}

@app.get("/plan-builder/plans")
def get_trading_plans():
    """Get all saved trading plans"""
    with Session(engine) as sess:
        plans = sess.exec(select(TradingPlan)).all()
        
        plan_summaries = []
        for plan in plans:
            plan_data = json.loads(plan.plan_data)
            summary = {
                "id": plan.id,
                "plan_name": plan.plan_name,
                "total_capital": plan.total_capital,
                "created_date": plan.created_date.isoformat(),
                "status": plan.status,
                "num_positions": len(plan_data.get("positions", [])),
                "total_allocation": plan_data.get("capital_info", {}).get("allocated_capital", 0),
                "total_risk": plan_data.get("risk_management", {}).get("total_risk_pct", 0)
            }
            plan_summaries.append(summary)
    
    return {"trading_plans": plan_summaries}

@app.get("/plan-builder/plans/{plan_id}")
def get_trading_plan(plan_id: int):
    """Get detailed trading plan by ID"""
    with Session(engine) as sess:
        plan = sess.get(TradingPlan, plan_id)
        if not plan:
            raise HTTPException(404, "Trading plan not found")
        
        plan_data = json.loads(plan.plan_data)
        plan_data["plan_id"] = plan.id
        plan_data["status"] = plan.status
        
        return {"trading_plan": plan_data}

@app.delete("/plan-builder/plans/{plan_id}")
def delete_trading_plan(plan_id: int):
    """Delete a trading plan"""
    with Session(engine) as sess:
        plan = sess.get(TradingPlan, plan_id)
        if not plan:
            raise HTTPException(404, "Trading plan not found")
        
        sess.delete(plan)
        sess.commit()
        
        return {"message": f"Trading plan '{plan.plan_name}' deleted successfully"}
