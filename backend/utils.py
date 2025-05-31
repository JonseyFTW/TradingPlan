import os, requests
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd
from polygon import RESTClient
from typing import Dict, List, Optional, Tuple

API_KEY = os.getenv("POLYGON_API_KEY")
polygon_client = RESTClient(API_KEY) if API_KEY else None

# Polygon index symbols
INDEX_SYMBOLS = {
    "nasdaq": "NDX",
    "sp500":  "SPX",
    "dow":    "DJI",
    "iwm":    "IWM"
}

@lru_cache(maxsize=10)
def get_constituents(index_name: str):
    """Get index constituents using Polygon official client"""
    print(f"🔍 CONSTITUENTS: Fetching {index_name} constituents using Polygon client...")
    
    if not polygon_client:
        print(f"❌ CONSTITUENTS: Polygon client not initialized (no API key)")
        raise ValueError("Polygon API key not available")
    
    try:
        # Map index names to market filters
        if index_name.lower() == "nasdaq":
            print(f"📊 CONSTITUENTS: Fetching NASDAQ-listed stocks...")
            # Get active stocks listed on NASDAQ
            tickers = polygon_client.list_tickers(
                market="stocks",
                exchange="XNAS",  # NASDAQ
                active=True,
                limit=1000
            )
            symbols = [t.ticker for t in tickers if t.ticker and not "." in t.ticker]
            print(f"✅ CONSTITUENTS: Found {len(symbols)} NASDAQ stocks")
            return symbols
            
        elif index_name.lower() == "sp500":
            print(f"📊 CONSTITUENTS: Fetching NYSE/NASDAQ large-cap stocks for S&P 500 approximation...")
            # Get large-cap stocks from major exchanges
            symbols = []
            
            # NASDAQ large caps
            nasdaq_tickers = polygon_client.list_tickers(
                market="stocks",
                exchange="XNAS",
                active=True,
                limit=500
            )
            symbols.extend([t.ticker for t in nasdaq_tickers if t.ticker and not "." in t.ticker])
            
            # NYSE large caps
            nyse_tickers = polygon_client.list_tickers(
                market="stocks", 
                exchange="XNYS",  # NYSE
                active=True,
                limit=500
            )
            symbols.extend([t.ticker for t in nyse_tickers if t.ticker and not "." in t.ticker])
            
            # Remove duplicates and limit
            unique_symbols = list(set(symbols))[:800]
            print(f"✅ CONSTITUENTS: Found {len(unique_symbols)} large-cap stocks")
            return unique_symbols
            
        elif index_name.lower() == "dow":
            print(f"📊 CONSTITUENTS: Using Dow Jones 30 components...")
            # Dow 30 components - these are relatively stable
            dow_30 = [
                "AAPL", "MSFT", "UNH", "GS", "HD", "CAT", "MCD", "V", "CRM", "HON",
                "AXP", "AMGN", "IBM", "TRV", "JPM", "JNJ", "PG", "CVX", "MRK", "WMT",
                "DIS", "MMM", "NKE", "KO", "CSCO", "INTC", "VZ", "WBA", "DOW", "BA"
            ]
            print(f"✅ CONSTITUENTS: Using {len(dow_30)} Dow 30 components")
            return dow_30
            
        elif index_name.lower() == "iwm" or index_name.lower() == "russell2000":
            print(f"📊 CONSTITUENTS: Fetching small-cap stocks for Russell 2000 approximation...")
            # Get smaller-cap stocks
            symbols = []
            
            # Get stocks from various exchanges with smaller market caps
            for exchange in ["XNAS", "XNYS", "BATS"]:
                try:
                    tickers = polygon_client.list_tickers(
                        market="stocks",
                        exchange=exchange,
                        active=True,
                        limit=600
                    )
                    symbols.extend([t.ticker for t in tickers if t.ticker and not "." in t.ticker])
                except:
                    continue
            
            # Remove duplicates and limit to reasonable size
            unique_symbols = list(set(symbols))[:1500]
            print(f"✅ CONSTITUENTS: Found {len(unique_symbols)} small/mid-cap stocks")
            return unique_symbols
            
        else:
            print(f"❌ CONSTITUENTS: Unknown index: {index_name}")
            raise ValueError(f"Unknown index: {index_name}")
            
    except Exception as e:
        print(f"⚠️ CONSTITUENTS: API error for {index_name}, falling back to curated lists: {e}")
        
        # Fallback to larger curated lists
        if index_name.lower() == "nasdaq":
            return get_curated_nasdaq_list()
        elif index_name.lower() == "sp500":
            return get_curated_sp500_list()
        elif index_name.lower() == "dow":
            return [
                "AAPL", "MSFT", "UNH", "GS", "HD", "CAT", "MCD", "V", "CRM", "HON",
                "AXP", "AMGN", "IBM", "TRV", "JPM", "JNJ", "PG", "CVX", "MRK", "WMT",
                "DIS", "MMM", "NKE", "KO", "CSCO", "INTC", "VZ", "WBA", "DOW", "BA"
            ]
        elif index_name.lower() == "iwm":
            return get_curated_russell2000_list()
        else:
            raise ValueError(f"Unknown index: {index_name}")

def get_curated_nasdaq_list():
    """Expanded NASDAQ list for fallback"""
    return [
        # NASDAQ 100 leaders
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "PEP", "ADBE", "CSCO", "CMCSA", "INTC", "TXN", "QCOM", "INTU",
        "ISRG", "AMGN", "HON", "BKNG", "VRTX", "SBUX", "GILD", "ADP", "ADI", "LRCX",
        "PYPL", "REGN", "MDLZ", "KLAC", "MRVL", "ORLY", "CRWD", "FTNT", "NXPI", "CTAS",
        "ABNB", "DDOG", "TEAM", "WDAY", "CHTR", "PAYX", "FAST", "ODFL", "VRSK", "EXC",
        # Additional NASDAQ growth stocks
        "ZM", "DOCU", "ROKU", "PTON", "ZS", "OKTA", "SNOW", "NET", "DKNG", "RBLX",
        "COIN", "HOOD", "SOFI", "PLTR", "RIVN", "LCID", "NIO", "XPEV", "LI", "TSLA",
        "MRNA", "BNTX", "ZTS", "ILMN", "BIIB", "CELG", "ALGN", "IDXX", "CTSH", "FISV",
        "INCY", "MXIM", "XLNX", "SWKS", "MPWR", "MCHP", "AMAT", "MU", "WDC", "STX",
        "NTAP", "FFIV", "JNPR", "ANET", "SMCI", "ENPH", "SEDG", "FSLR", "SPWR", "PLUG"
    ]

def get_curated_sp500_list():
    """Expanded S&P 500 list for fallback"""
    return [
        # Large cap leaders
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "BRK.B", "TSLA", "UNH",
        "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "LLY", "ABBV",
        "AVGO", "PFE", "KO", "MRK", "COST", "BAC", "PEP", "TMO", "WMT", "CRM",
        "CSCO", "ABT", "MCD", "DIS", "DHR", "ADBE", "VZ", "CMCSA", "ACN", "NFLX",
        "BMY", "TXN", "WFC", "NEE", "PM", "ORCL", "COP", "LIN", "AMD", "UPS",
        # Additional S&P 500 components
        "LOW", "T", "MS", "RTX", "SPGI", "HON", "INTU", "IBM", "CAT", "GS",
        "AXP", "BA", "MMM", "TRV", "AIG", "C", "USB", "PNC", "TFC", "COF",
        "SCHW", "BLK", "AMT", "CCI", "PLD", "EQIX", "DLR", "PSA", "EXR", "AVB",
        "UDR", "ESS", "MAA", "CPT", "EQR", "AIV", "HST", "REG", "BXP", "VTR",
        "WELL", "PEAK", "HR", "SLG", "KIM", "DEI", "SPG", "TCO", "MAC", "CBL"
    ]

def get_curated_russell2000_list():
    """Small/mid-cap stocks for Russell 2000 approximation"""
    return [
        # Small cap growth
        "SMAR", "TENB", "SUMO", "BILL", "DDOG", "CRWD", "ZS", "NET", "OKTA", "SNOW",
        "DOCN", "FSLY", "ESTC", "MDB", "TEAM", "WDAY", "VEEV", "CRM", "NOW", "HUBS",
        # Small cap value 
        "OMCL", "HELE", "POOL", "WSO", "CVCO", "ROLL", "UFPI", "BCC", "TREX", "AZEK",
        "BECN", "CR", "MLI", "AAON", "AIT", "GTLS", "NHC", "PINC", "CALM", "JJSF",
        # Small cap tech
        "RGEN", "ALRM", "ARLO", "VCYT", "PACB", "RXDX", "BEAM", "EDIT", "CRSP", "NTLA",
        "BLUE", "FOLD", "ARWR", "SAGE", "SRPT", "BMRN", "RARE", "ACAD", "HALO", "ZLAB",
        # Small cap industrials
        "ESAB", "CARR", "OTIS", "IR", "GNRC", "XYL", "IEX", "FLS", "PUMP", "TTC",
        "FLOW", "CNM", "GGG", "WMTS", "BRC", "WWD", "SKX", "HBI", "UAA", "LEVI",
        # Small cap consumer
        "PRGS", "UPWK", "ETSY", "W", "CHWY", "PETS", "WOOF", "BARK", "BIG", "FIVE",
        "DLTR", "DG", "COST", "BJ", "PSMT", "CHEF", "EAT", "CAKE", "TXRH", "SHAK"
    ]

def fetch_ohlcv(symbol: str, months: int = 3):
    """Fetch OHLCV data using Polygon official client"""
    from datetime import datetime, timedelta
    import pandas as pd
    
    if not polygon_client:
        print(f"❌ FETCH_OHLCV: Polygon client not available for {symbol}")
        return pd.DataFrame()
    
    try:
        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=30*months)
        
        # Use polygon client to get aggregates
        aggs = polygon_client.get_aggs(
            ticker=symbol,
            multiplier=1,
            timespan="day",
            from_=from_date.strftime("%Y-%m-%d"),
            to=to_date.strftime("%Y-%m-%d"),
            adjusted=True,
            sort="asc",
            limit=5000
        )
        
        if not aggs or len(aggs) == 0:
            print(f"⚠️ FETCH_OHLCV: No data returned for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for agg in aggs:
            data.append({
                "timestamp": agg.timestamp,
                "Open": agg.open,
                "High": agg.high,
                "Low": agg.low,
                "Close": agg.close,
                "Volume": agg.volume
            })
        
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df.index.name = "Date"
        
        return df[["Open","High","Low","Close","Volume"]]
        
    except Exception as e:
        print(f"❌ FETCH_OHLCV: Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def get_fundamentals(symbol: str):
    """Get basic fundamentals using Polygon client"""
    if not polygon_client:
        return {"error": "Polygon client not available"}
    try:
        # Note: This endpoint might need a higher tier plan
        return {"symbol": symbol, "note": "Fundamentals require higher tier plan"}
    except Exception as e:
        return {"error": str(e)}

def get_earnings(symbol: str):
    """Get earnings data using Polygon client"""
    if not polygon_client:
        return {"error": "Polygon client not available"}
    try:
        # Note: This endpoint might need a higher tier plan
        return {"symbol": symbol, "note": "Earnings data require higher tier plan"}
    except Exception as e:
        return {"error": str(e)}

def get_earnings_calendar():
    """Get earnings calendar using Polygon client"""
    if not polygon_client:
        return {"error": "Polygon client not available"}
    try:
        # Note: This endpoint might need a higher tier plan
        return {"note": "Earnings calendar requires higher tier plan"}
    except Exception as e:
        return {"error": str(e)}

def get_news(symbol: str):
    """Get news using Polygon client"""
    if not polygon_client:
        return {"error": "Polygon client not available"}
    try:
        news = polygon_client.list_ticker_news(ticker=symbol, limit=10)
        return {"results": [{"title": n.title, "published_utc": n.published_utc, "summary": getattr(n, 'summary', '')} for n in news]}
    except Exception as e:
        return {"error": str(e)}

def get_options_open_interest(symbol: str):
    """Get options open interest using Polygon client"""
    if not polygon_client:
        return {"error": "Polygon client not available"}
    try:
        # Note: Options data might need a higher tier plan
        return {"symbol": symbol, "note": "Options data require higher tier plan"}
    except Exception as e:
        return {"error": str(e)}

# ENHANCED SCREENING FUNCTIONS

def get_ticker_details(symbol: str):
    """Get detailed ticker information using Polygon client"""
    if not polygon_client:
        return {"sic_description": "Unknown"}
    
    try:
        ticker_details = polygon_client.get_ticker_details(symbol)
        return {
            "sic_description": getattr(ticker_details, 'sic_description', 'Unknown'),
            "market_cap": getattr(ticker_details, 'market_cap', 0),
            "share_class_shares_outstanding": getattr(ticker_details, 'share_class_shares_outstanding', 0)
        }
    except Exception as e:
        print(f"⚠️ TICKER_DETAILS: Could not get details for {symbol}: {e}")
        return {"sic_description": "Unknown"}

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
    
    # Process EVERY single stock found across all indices - no artificial limits
    process_limit = len(symbols)  # Scan the complete market universe
    
    print(f"🔍 SCREENING: Starting COMPLETE market screen of {len(symbols)} symbols")
    print(f"📊 SCREENING: Filters - Price: ${min_price}-${max_price}, Volume: {min_volume:,}")
    print(f"🎯 SCREENING: Required patterns: {required_patterns}")
    
    processed = 0
    skipped = 0
    progress_interval = max(100, len(symbols) // 20)  # Report progress every 5%
    
    for symbol in symbols[:process_limit]:
        try:
            processed += 1
            
            # Progress reporting every 5% of total universe
            if processed % progress_interval == 0:
                progress_pct = (processed / len(symbols)) * 100
                print(f"📈 SCREENING: Progress {processed:,}/{len(symbols):,} ({progress_pct:.1f}%) - Found {len(results):,} stocks so far")
            
            # Fetch shorter timeframe for faster screening
            df = fetch_ohlcv(symbol, months=2)
            if df.empty:
                skipped += 1
                continue
                
            current_price = df["Close"].iloc[-1]
            current_volume = df["Volume"].iloc[-1]
            
            # Basic filters
            if current_price < min_price or current_price > max_price:
                skipped += 1
                continue
            if current_volume < min_volume:
                skipped += 1
                continue
                
            # Skip expensive market cap calculation if not filtering by it
            market_cap = 0
            if min_market_cap > 0 or max_market_cap < float('inf'):
                try:
                    market_cap = get_market_cap(symbol)
                    if market_cap > 0 and (market_cap < min_market_cap or market_cap > max_market_cap):
                        skipped += 1
                        continue
                except:
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
            # Only log successful matches, not every processing step
            if patterns_found or current_price > 50:  # Log interesting stocks
                print(f"✅ SCREENING: Added {symbol} - ${current_price:.2f}, Patterns: {patterns_found}")
            
        except Exception as e:
            # Reduce error logging noise
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
