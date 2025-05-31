import os, requests
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd

API_KEY = os.getenv("POLYGON_API_KEY")

# Polygon index symbols
INDEX_SYMBOLS = {
    "nasdaq": "NDX",
    "sp500":  "SPX",
    "dow":    "DJI"
}

@lru_cache(maxsize=3)
def get_constituents(index_name: str):
    print(f"🔍 CONSTITUENTS: Fetching {index_name} constituents...")
    print(f"🔑 CONSTITUENTS: API_KEY exists: {bool(API_KEY)}")
    
    idx = INDEX_SYMBOLS.get(index_name.lower())
    if not idx:
        print(f"❌ CONSTITUENTS: Unknown index: {index_name}")
        raise ValueError("Unknown index")
    
    url = (
      f"https://api.polygon.io/v3/reference/index_constituents"
      f"?symbol={idx}&apiKey={API_KEY}"
    )
    print(f"📡 CONSTITUENTS: Making request to: {url[:50]}...")
    
    try:
        res = requests.get(url, timeout=10)
        print(f"📊 CONSTITUENTS: Response status: {res.status_code}")
        res.raise_for_status()
        data = res.json()
        results = data.get("results", [])
        print(f"📈 CONSTITUENTS: Got {len(results)} initial results")
        
        tickers = [r["ticker"] for r in results]
        
        # handle pagination
        next_url = data.get("next_url")
        page_count = 1
        while next_url and page_count < 5:  # Limit pagination to avoid infinite loops
            page_count += 1
            print(f"📄 CONSTITUENTS: Fetching page {page_count}...")
            res = requests.get(next_url + f"&apiKey={API_KEY}", timeout=10)
            res.raise_for_status()
            data = res.json()
            page_results = data.get("results", [])
            tickers += [r["ticker"] for r in page_results]
            print(f"📈 CONSTITUENTS: Page {page_count} added {len(page_results)} results")
            next_url = data.get("next_url")
        
        print(f"✅ CONSTITUENTS: Successfully fetched {len(tickers)} tickers for {index_name}")
        return tickers
        
    except requests.exceptions.Timeout:
        print(f"⏰ CONSTITUENTS: Timeout fetching {index_name}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"❌ CONSTITUENTS: Request error for {index_name}: {e}")
        raise
    except Exception as e:
        print(f"❌ CONSTITUENTS: Unexpected error for {index_name}: {e}")
        raise

def fetch_ohlcv(symbol:str, months:int=3):
    from datetime import datetime, timedelta
    import pandas as pd
    to_date   = datetime.utcnow().date()
    from_date = to_date - timedelta(days=30*months)
    url = (
      f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/"
      f"{from_date}/{to_date}"
      f"?adjusted=true&sort=asc&limit=5000&apiKey={API_KEY}"
    )
    res = requests.get(url); res.raise_for_status()
    results = res.json().get("results", [])
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df.set_index("t", inplace=True)
    df.rename(columns={"o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"}, inplace=True)
    return df[["Open","High","Low","Close","Volume"]]

def get_fundamentals(symbol:str):
    # example: get basic fundamentals
    res = requests.get(
      f"https://api.polygon.io/v1/meta/symbols/{symbol}/company?apiKey={API_KEY}"
    ); res.raise_for_status()
    return res.json()

def get_earnings(symbol:str):
    res = requests.get(
      f"https://api.polygon.io/v1/meta/symbols/{symbol}/earnings?apiKey={API_KEY}"
    ); res.raise_for_status()
    return res.json()

def get_earnings_calendar():
    res = requests.get(
      f"https://api.polygon.io/v1/calendar/earnings?apiKey={API_KEY}"
    ); res.raise_for_status()
    return res.json()

def get_news(symbol:str):
    res = requests.get(
      f"https://api.polygon.io/v2/reference/news?ticker={symbol}&apiKey={API_KEY}"
    ); res.raise_for_status()
    return res.json()

def get_options_open_interest(symbol:str):
    res = requests.get(
      f"https://api.polygon.io/v2/options/open-interest/{symbol}?apiKey={API_KEY}"
    ); res.raise_for_status()
    return res.json()

# ENHANCED SCREENING FUNCTIONS

def get_ticker_details(symbol: str):
    """Get detailed ticker information including market cap, sector, etc."""
    try:
        res = requests.get(
            f"https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={API_KEY}"
        )
        res.raise_for_status()
        return res.json().get("results", {})
    except:
        return {}

def get_market_cap(symbol: str):
    """Get market capitalization for a symbol"""
    details = get_ticker_details(symbol)
    shares = details.get("share_class_shares_outstanding", 0)
    price_data = fetch_ohlcv(symbol, months=1)
    if price_data.empty:
        return 0
    current_price = price_data["Close"].iloc[-1]
    return shares * current_price

def calculate_volume_metrics(df):
    """Calculate volume-based metrics"""
    if df.empty or len(df) < 20:
        return {}
    
    avg_volume_20d = df["Volume"].rolling(20).mean().iloc[-1]
    current_volume = df["Volume"].iloc[-1]
    volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
    
    return {
        "avg_volume_20d": int(avg_volume_20d),
        "current_volume": int(current_volume),
        "volume_ratio": round(volume_ratio, 2),
        "volume_spike": bool(volume_ratio > 2.0)
    }

def detect_gap_up(df, min_gap_percent=2.0):
    """Detect gap up patterns"""
    if df.empty or len(df) < 2:
        return False
    
    today_open = df["Open"].iloc[-1]
    yesterday_close = df["Close"].iloc[-2]
    gap_percent = ((today_open - yesterday_close) / yesterday_close) * 100
    
    return bool(gap_percent >= min_gap_percent)

def detect_breakout_pattern(df, lookback_days=20):
    """Detect breakout above resistance"""
    if df.empty or len(df) < lookback_days + 1:
        return False
    
    # Calculate resistance level (highest high in lookback period excluding today)
    resistance = df["High"].iloc[-(lookback_days+1):-1].max()
    current_high = df["High"].iloc[-1]
    
    return bool(current_high > resistance * 1.02)  # 2% breakout threshold

def detect_momentum_pattern(df):
    """Detect momentum patterns using price action"""
    if df.empty or len(df) < 5:
        return False
    
    # Check for consecutive higher closes
    recent_closes = df["Close"].tail(5)
    higher_closes = all(recent_closes.iloc[i] > recent_closes.iloc[i-1] for i in range(1, len(recent_closes)))
    
    # Check for increasing volume trend
    recent_volumes = df["Volume"].tail(5)
    volume_trend = recent_volumes.iloc[-1] > recent_volumes.mean()
    
    return bool(higher_closes and volume_trend)

def screen_stocks(symbols, filters=None):
    """Screen stocks based on multiple criteria"""
    if filters is None:
        filters = {}
    
    results = []
    
    min_price = filters.get("min_price", 5)
    max_price = filters.get("max_price", 500)
    min_volume = filters.get("min_volume", 100000)
    min_market_cap = filters.get("min_market_cap", 100000000)  # 100M
    max_market_cap = filters.get("max_market_cap", float('inf'))
    required_patterns = filters.get("patterns", [])  # ["gap_up", "breakout", "momentum"]
    
    print(f"🔍 SCREENING: Starting screen of {len(symbols)} symbols")
    print(f"📊 SCREENING: Filters - Price: ${min_price}-${max_price}, Volume: {min_volume:,}, Market Cap: ${min_market_cap:,}")
    print(f"🎯 SCREENING: Required patterns: {required_patterns}")
    
    processed = 0
    skipped = 0
    
    for symbol in symbols[:30]:  # Limit to avoid API limits
        try:
            processed += 1
            print(f"📈 SCREENING: Processing {symbol} ({processed}/30)")
            
            df = fetch_ohlcv(symbol, months=3)
            if df.empty:
                print(f"⚠️ SCREENING: No data for {symbol}")
                skipped += 1
                continue
                
            current_price = df["Close"].iloc[-1]
            current_volume = df["Volume"].iloc[-1]
            
            # Basic filters
            if current_price < min_price or current_price > max_price:
                print(f"❌ SCREENING: {symbol} price ${current_price:.2f} outside range ${min_price}-${max_price}")
                skipped += 1
                continue
            if current_volume < min_volume:
                print(f"❌ SCREENING: {symbol} volume {current_volume:,} below minimum {min_volume:,}")
                skipped += 1
                continue
                
            # Market cap filter (skip if can't get market cap data)
            try:
                market_cap = get_market_cap(symbol)
                if market_cap > 0 and (market_cap < min_market_cap or market_cap > max_market_cap):
                    print(f"❌ SCREENING: {symbol} market cap ${market_cap:,} outside range")
                    skipped += 1
                    continue
            except:
                print(f"⚠️ SCREENING: Could not get market cap for {symbol}, including anyway")
                market_cap = 0
            
            # Pattern detection
            patterns_found = []
            if "gap_up" in required_patterns and detect_gap_up(df):
                patterns_found.append("gap_up")
            if "breakout" in required_patterns and detect_breakout_pattern(df):
                patterns_found.append("breakout")
            if "momentum" in required_patterns and detect_momentum_pattern(df):
                patterns_found.append("momentum")
            
            # Check if all required patterns are present
            if required_patterns and not all(pattern in patterns_found for pattern in required_patterns):
                print(f"❌ SCREENING: {symbol} missing required patterns. Found: {patterns_found}, Required: {required_patterns}")
                skipped += 1
                continue
            
            volume_metrics = calculate_volume_metrics(df)
            ticker_details = get_ticker_details(symbol)
            
            result = {
                "symbol": symbol,
                "price": round(current_price, 2),
                "volume": int(current_volume),
                "market_cap": int(market_cap) if market_cap > 0 else 0,
                "sector": ticker_details.get("sic_description", "Unknown"),
                "patterns": patterns_found,
                "volume_metrics": volume_metrics
            }
            results.append(result)
            print(f"✅ SCREENING: Added {symbol} to results - Price: ${current_price:.2f}, Patterns: {patterns_found}")
            
        except Exception as e:
            print(f"❌ SCREENING: Error processing {symbol}: {e}")
            skipped += 1
            continue
    
    print(f"🏁 SCREENING: Completed. Found {len(results)} stocks, skipped {skipped}")
    return sorted(results, key=lambda x: x["volume_metrics"].get("volume_ratio", 0), reverse=True)

def get_sector_performance():
    """Get sector ETF performance for sector rotation analysis"""
    sector_etfs = {
        "Technology": "XLK",
        "Healthcare": "XLV", 
        "Financials": "XLF",
        "Consumer Discretionary": "XLY",
        "Communication": "XLC",
        "Industrials": "XLI",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Materials": "XLB"
    }
    
    performance = {}
    
    for sector, etf in sector_etfs.items():
        try:
            df = fetch_ohlcv(etf, months=1)
            if not df.empty and len(df) >= 20:
                # Calculate performance metrics
                current_price = df["Close"].iloc[-1]
                price_20d_ago = df["Close"].iloc[-20] if len(df) >= 20 else df["Close"].iloc[0]
                price_5d_ago = df["Close"].iloc[-5] if len(df) >= 5 else df["Close"].iloc[0]
                
                performance[sector] = {
                    "symbol": etf,
                    "current_price": round(current_price, 2),
                    "performance_1d": round(((df["Close"].iloc[-1] / df["Close"].iloc[-2]) - 1) * 100, 2) if len(df) >= 2 else 0,
                    "performance_5d": round(((current_price / price_5d_ago) - 1) * 100, 2),
                    "performance_20d": round(((current_price / price_20d_ago) - 1) * 100, 2),
                    "relative_strength": 0  # Will be calculated vs SPY
                }
        except Exception as e:
            print(f"Error getting {sector} performance: {e}")
            
    # Calculate relative strength vs SPY
    try:
        spy_df = fetch_ohlcv("SPY", months=1)
        if not spy_df.empty and len(spy_df) >= 20:
            spy_20d_return = ((spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-20]) - 1) * 100
            
            for sector in performance:
                sector_20d_return = performance[sector]["performance_20d"]
                performance[sector]["relative_strength"] = round(sector_20d_return - spy_20d_return, 2)
    except:
        pass
    
    return performance

def get_market_breadth():
    """Get market breadth indicators"""
    try:
        # Get S&P 500 data
        spy_df = fetch_ohlcv("SPY", months=1)
        if spy_df.empty:
            return {}
            
        # Calculate basic breadth metrics
        current_price = spy_df["Close"].iloc[-1]
        sma_20 = spy_df["Close"].rolling(20).mean().iloc[-1]
        sma_50 = spy_df["Close"].rolling(50).mean().iloc[-1] if len(spy_df) >= 50 else sma_20
        
        # Get VIX data (volatility)
        vix_df = fetch_ohlcv("VIX", months=1)
        current_vix = vix_df["Close"].iloc[-1] if not vix_df.empty else 20
        
        return {
            "spy_price": round(current_price, 2),
            "spy_vs_sma20": round(((current_price / sma_20) - 1) * 100, 2),
            "spy_vs_sma50": round(((current_price / sma_50) - 1) * 100, 2),
            "vix": round(current_vix, 2),
            "market_regime": "RISK_ON" if current_vix < 20 and current_price > sma_20 else "RISK_OFF"
        }
    except:
        return {"error": "Unable to fetch market breadth data"}
