import pandas as pd, pandas_ta as ta
from utils import fetch_ohlcv, get_ticker_details
import numpy as np
import json

def clean_nan(value):
    """Convert NaN/inf values to None for JSON serialization"""
    if pd.isna(value) or np.isinf(value):
        return None
    return float(value)

def interpret_rsi(rsi):
    """Interpret RSI values with trading context"""
    if rsi is None:
        return "RSI data unavailable"
    elif rsi >= 70:
        return f"RSI {rsi:.1f} - OVERBOUGHT: Strong selling pressure expected. Consider taking profits or waiting for pullback."
    elif rsi >= 60:
        return f"RSI {rsi:.1f} - BULLISH: Strong upward momentum but approaching overbought territory. Monitor for reversal signals."
    elif rsi >= 40:
        return f"RSI {rsi:.1f} - NEUTRAL: Balanced momentum. Wait for clearer directional signals before entry."
    elif rsi >= 30:
        return f"RSI {rsi:.1f} - BEARISH: Downward momentum present. Look for support levels before considering entry."
    else:
        return f"RSI {rsi:.1f} - OVERSOLD: Potential buying opportunity as selling pressure may be exhausted. Look for reversal confirmation."

def interpret_macd(macd, signal=None):
    """Interpret MACD values with trading context"""
    if macd is None:
        return "MACD data unavailable"
    
    if macd > 0:
        strength = "strong" if abs(macd) > 1 else "moderate"
        return f"MACD {macd:.3f} - BULLISH: Positive value suggests upward momentum. {strength.title()} buy signal when above signal line."
    elif macd < 0:
        strength = "strong" if abs(macd) > 1 else "moderate"
        return f"MACD {macd:.3f} - BEARISH: Negative value suggests downward momentum. {strength.title()} sell signal when below signal line."
    else:
        return f"MACD {macd:.3f} - NEUTRAL: Momentum at equilibrium. Watch for directional breakout."

def interpret_adx(adx):
    """Interpret ADX values with trend strength context"""
    if adx is None:
        return "ADX data unavailable"
    elif adx >= 50:
        return f"ADX {adx:.1f} - VERY STRONG TREND: Extremely strong trending market. High probability trend continuation."
    elif adx >= 25:
        return f"ADX {adx:.1f} - STRONG TREND: Clear trending market. Good for trend-following strategies."
    elif adx >= 20:
        return f"ADX {adx:.1f} - EMERGING TREND: Trend is developing. Monitor for strength confirmation."
    else:
        return f"ADX {adx:.1f} - WEAK/NO TREND: Choppy, sideways market. Avoid trend-following strategies."

def interpret_bollinger_bands(price, bb_upper, bb_lower):
    """Interpret Bollinger Band position"""
    if bb_upper is None or bb_lower is None:
        return "Bollinger Bands data unavailable"
    
    bb_width = bb_upper - bb_lower
    bb_position = (price - bb_lower) / bb_width * 100
    
    if bb_position >= 80:
        return f"Price near upper band ({bb_position:.0f}%) - OVERBOUGHT: High probability of pullback to middle band."
    elif bb_position >= 60:
        return f"Price in upper zone ({bb_position:.0f}%) - BULLISH: Strong upward momentum, but watch for resistance."
    elif bb_position >= 40:
        return f"Price near middle band ({bb_position:.0f}%) - NEUTRAL: Balanced between support and resistance."
    elif bb_position >= 20:
        return f"Price in lower zone ({bb_position:.0f}%) - BEARISH: Downward pressure, but potential support nearby."
    else:
        return f"Price near lower band ({bb_position:.0f}%) - OVERSOLD: High probability of bounce to middle band."

def generate_risk_factors(indicators, score, symbol):
    """Generate comprehensive risk assessment"""
    risks = []
    
    # Volatility risk from ATR
    if indicators.get('ATR') and indicators.get('ATR') > 5:
        risks.append(f"HIGH VOLATILITY: ATR of {indicators['ATR']:.2f} indicates significant price swings. Use smaller position sizes.")
    
    # Momentum divergence risks
    rsi = indicators.get('RSI')
    if rsi and (rsi > 75 or rsi < 25):
        risks.append("MOMENTUM EXTREME: RSI at extreme levels increases reversal probability. Consider profit-taking or wait for better entry.")
    
    # Trend strength risks
    adx = indicators.get('ADX')
    if adx and adx < 20:
        risks.append("WEAK TREND: Low ADX suggests choppy, directionless market. Trend-following strategies may fail.")
    
    # Score-based risks
    if score < 5:
        risks.append("LOW CONVICTION SETUP: Poor technical alignment. Consider waiting for better opportunity.")
    
    # General market risks
    risks.extend([
        f"NEWS SENSITIVITY: {symbol} may react strongly to earnings, FDA approvals, or industry developments. Monitor news flow.",
        "MARKET CONDITIONS: Broader market trends and sector rotation can override individual stock technicals.",
        "LIQUIDITY RISK: Ensure adequate volume for planned position size to avoid slippage on entry/exit."
    ])
    
    return risks

def generate_fibonacci_context(fibs, price):
    """Generate Fibonacci level context and analysis"""
    current_level = None
    for level, fib_price in fibs.items():
        if abs(price - fib_price) < (max(fibs.values()) - min(fibs.values())) * 0.05:  # Within 5% of fib level
            current_level = level
            break
    
    if current_level:
        return f"Current price near {current_level} Fibonacci level (${fibs[current_level]:.2f}) - This often acts as significant support or resistance."
    else:
        # Find closest levels
        above = {k: v for k, v in fibs.items() if v > price}
        below = {k: v for k, v in fibs.items() if v < price}
        
        if above and below:
            closest_above = min(above.items(), key=lambda x: x[1])
            closest_below = max(below.items(), key=lambda x: x[1])
            return f"Price between {closest_below[0]} (${closest_below[1]:.2f}) and {closest_above[0]} (${closest_above[1]:.2f}) Fibonacci levels."
        
    return "Price outside primary Fibonacci retracement zones."

def calculate_relative_strength(symbol, df):
    """Calculate relative strength vs SPY and sector ETF"""
    try:
        # Get SPY data for comparison
        spy_df = fetch_ohlcv("SPY", months=3)
        if spy_df.empty:
            return {"error": "Cannot fetch SPY data for relative strength calculation"}
        
        # Align dates and calculate returns
        common_dates = df.index.intersection(spy_df.index)
        if len(common_dates) < 20:
            return {"error": "Insufficient overlapping data for relative strength calculation"}
        
        # Get returns for overlapping period
        stock_returns = df.loc[common_dates, "Close"].pct_change().dropna()
        spy_returns = spy_df.loc[common_dates, "Close"].pct_change().dropna()
        
        # Calculate relative strength metrics
        stock_perf_20d = ((df["Close"].iloc[-1] / df["Close"].iloc[-20]) - 1) * 100 if len(df) >= 20 else 0
        spy_perf_20d = ((spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-20]) - 1) * 100 if len(spy_df) >= 20 else 0
        
        stock_perf_5d = ((df["Close"].iloc[-1] / df["Close"].iloc[-5]) - 1) * 100 if len(df) >= 5 else 0
        spy_perf_5d = ((spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-5]) - 1) * 100 if len(spy_df) >= 5 else 0
        
        # Relative strength vs SPY
        rs_vs_spy_20d = stock_perf_20d - spy_perf_20d
        rs_vs_spy_5d = stock_perf_5d - spy_perf_5d
        
        # Calculate beta (sensitivity to market moves)
        if len(stock_returns) >= 20 and len(spy_returns) >= 20:
            beta = np.cov(stock_returns, spy_returns)[0,1] / np.var(spy_returns)
        else:
            beta = 1.0
        
        # Get sector information for sector relative strength
        sector_rs = {"error": "Sector data unavailable"}
        try:
            ticker_details = get_ticker_details(symbol)
            sector_description = ticker_details.get("sic_description", "")
            
            # Map to sector ETFs (simplified mapping)
            sector_etf_map = {
                "technology": "XLK",
                "software": "XLK", 
                "computer": "XLK",
                "pharmaceutical": "XLV",
                "biotechnology": "XLV",
                "healthcare": "XLV",
                "financial": "XLF",
                "bank": "XLF",
                "retail": "XLY",
                "consumer": "XLY",
                "energy": "XLE",
                "oil": "XLE",
                "utility": "XLU",
                "electric": "XLU",
                "industrial": "XLI",
                "manufacturing": "XLI"
            }
            
            sector_etf = None
            for keyword, etf in sector_etf_map.items():
                if keyword.lower() in sector_description.lower():
                    sector_etf = etf
                    break
            
            if sector_etf:
                sector_df = fetch_ohlcv(sector_etf, months=3)
                if not sector_df.empty and len(sector_df) >= 20:
                    sector_perf_20d = ((sector_df["Close"].iloc[-1] / sector_df["Close"].iloc[-20]) - 1) * 100
                    rs_vs_sector = stock_perf_20d - sector_perf_20d
                    sector_rs = {
                        "sector_etf": sector_etf,
                        "sector_performance_20d": round(sector_perf_20d, 2),
                        "relative_strength_vs_sector": round(rs_vs_sector, 2),
                        "outperforming_sector": bool(rs_vs_sector > 0)
                    }
        except:
            pass
        
        return {
            "vs_spy": {
                "stock_performance_20d": round(stock_perf_20d, 2),
                "stock_performance_5d": round(stock_perf_5d, 2),
                "spy_performance_20d": round(spy_perf_20d, 2),
                "spy_performance_5d": round(spy_perf_5d, 2),
                "relative_strength_20d": round(rs_vs_spy_20d, 2),
                "relative_strength_5d": round(rs_vs_spy_5d, 2),
                "outperforming_market_20d": bool(rs_vs_spy_20d > 0),
                "outperforming_market_5d": bool(rs_vs_spy_5d > 0),
                "beta": round(beta, 2)
            },
            "vs_sector": sector_rs,
            "interpretation": generate_relative_strength_interpretation(rs_vs_spy_20d, rs_vs_spy_5d, beta)
        }
    except Exception as e:
        return {"error": f"Relative strength calculation failed: {str(e)}"}

def generate_relative_strength_interpretation(rs_20d, rs_5d, beta):
    """Generate interpretation of relative strength metrics"""
    interpretations = []
    
    # 20-day relative strength
    if rs_20d > 5:
        interpretations.append(f"STRONG OUTPERFORMANCE: Stock outperforming SPY by {rs_20d:.1f}% over 20 days - shows strong relative momentum.")
    elif rs_20d > 0:
        interpretations.append(f"MODEST OUTPERFORMANCE: Stock outperforming SPY by {rs_20d:.1f}% over 20 days - positive relative trend.")
    elif rs_20d > -5:
        interpretations.append(f"SLIGHT UNDERPERFORMANCE: Stock underperforming SPY by {abs(rs_20d):.1f}% over 20 days - market keeping pace.")
    else:
        interpretations.append(f"SIGNIFICANT UNDERPERFORMANCE: Stock underperforming SPY by {abs(rs_20d):.1f}% over 20 days - weak relative strength.")
    
    # 5-day trend
    if rs_5d > 2:
        interpretations.append(f"RECENT STRENGTH: Strong 5-day outperformance ({rs_5d:.1f}%) suggests accelerating momentum.")
    elif rs_5d < -2:
        interpretations.append(f"RECENT WEAKNESS: Poor 5-day performance ({rs_5d:.1f}%) suggests momentum loss.")
    
    # Beta interpretation
    if beta > 1.5:
        interpretations.append(f"HIGH BETA ({beta:.1f}): Stock is highly sensitive to market moves - expect amplified volatility.")
    elif beta < 0.5:
        interpretations.append(f"LOW BETA ({beta:.1f}): Stock moves independently of market - defensive characteristics.")
    else:
        interpretations.append(f"MODERATE BETA ({beta:.1f}): Stock moves roughly in line with market volatility.")
    
    return " ".join(interpretations)

def analyze_ticker(symbol: str):
    df = fetch_ohlcv(symbol)
    if df.empty:
        return {"error": f"No data for {symbol}"}

    # Fibonacci levels
    low, high = df["Low"].min(), df["High"].max()
    diff = high - low
    fibs = {f"{int(r*100)}%": round(high - diff*r,2)
            for r in (0.236,0.382,0.5,0.618,0.786)}

    # Indicators
    df["RSI"] = ta.rsi(df["Close"], length=14)
    macd = ta.macd(df["Close"])
    df = pd.concat([df, macd], axis=1).dropna()
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    df["ADX"] = ta.adx(df["High"], df["Low"], df["Close"], length=14)["ADX_14"]
    bb = ta.bbands(df["Close"], length=20)
    df = pd.concat([df, bb], axis=1)

    latest = df.iloc[-1]
    # Clean timeseries data to handle NaN values
    ts = {
      "dates":       df.index.strftime("%Y-%m-%d").tolist(),
      "closes":      df["Close"].round(2).tolist(),
      "volumes":     df["Volume"].astype(int).tolist(),
      "RSI":         [clean_nan(x) for x in df["RSI"].tolist()],
      "MACD":        [clean_nan(x) for x in df["MACD_12_26_9"].tolist()],
      "MACD_signal": [clean_nan(x) for x in df["MACDs_12_26_9"].tolist()],
      "ATR":         [clean_nan(x) for x in df["ATR"].tolist()],
      "ADX":         [clean_nan(x) for x in df["ADX"].tolist()],
      "BB_upper":    [clean_nan(x) for x in df["BBU_20_2.0"].tolist()],
      "BB_lower":    [clean_nan(x) for x in df["BBL_20_2.0"].tolist()],
    }

    # Simple composite score with NaN handling
    rsi_score = 0 if pd.isna(latest["RSI"]) else (50 - abs(latest["RSI"] - 50)) * 0.3
    macd_score = 0 if pd.isna(latest["MACD_12_26_9"]) else latest["MACD_12_26_9"] * 0.3
    vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
    vol_score = 0 if pd.isna(vol_avg) or vol_avg == 0 else (latest["Volume"] / vol_avg) * 0.2
    adx_score = 0 if pd.isna(latest["ADX"]) else (latest["ADX"] / 100) * 0.2
    
    score = rsi_score + macd_score + vol_score + adx_score

    plan = {
      "entry":     [fibs["61%"], fibs["50%"]],
      "stop_loss": round(fibs["61%"] * 0.95,2),
      "targets": [
        {"price": fibs["38%"], "pct": 30},
        {"price": fibs["23%"], "pct": 40},
        {"price": round(high,2), "pct": 30}
      ],
      "trail_after": {"trigger": fibs["23%"],
                      "distance": round(0.1*latest["Close"],2)}
    }

    # Generate rich analysis with context
    indicators_data = {
        "RSI":   clean_nan(latest["RSI"]),
        "MACD":  clean_nan(latest["MACD_12_26_9"]),
        "Volume": int(latest["Volume"]),
        "ATR":   clean_nan(latest["ATR"]),
        "ADX":   clean_nan(latest["ADX"]),
        "BB_upper": clean_nan(latest["BBU_20_2.0"]),
        "BB_lower": clean_nan(latest["BBL_20_2.0"])
    }
    
    # Generate contextual analysis
    analysis_insights = {
        "rsi_analysis": interpret_rsi(indicators_data["RSI"]),
        "macd_analysis": interpret_macd(indicators_data["MACD"]),
        "adx_analysis": interpret_adx(indicators_data["ADX"]),
        "bollinger_analysis": interpret_bollinger_bands(latest["Close"], indicators_data["BB_upper"], indicators_data["BB_lower"]),
        "fibonacci_analysis": generate_fibonacci_context(fibs, latest["Close"]),
        "risk_factors": generate_risk_factors(indicators_data, clean_nan(score) or 0, symbol.upper()),
        "volume_analysis": f"Current volume: {indicators_data['Volume']:,} shares. Average 20-day volume: {int(df['Volume'].rolling(20).mean().iloc[-1]):,} shares." if not pd.isna(df['Volume'].rolling(20).mean().iloc[-1]) else "Volume data insufficient for analysis."
    }
    
    # Trading summary
    if clean_nan(score) or 0 >= 10:
        conviction = "HIGH"
        recommendation = "Strong technical setup with multiple confirming indicators. Good risk/reward opportunity."
    elif clean_nan(score) or 0 >= 5:
        conviction = "MODERATE" 
        recommendation = "Mixed signals present. Proceed with caution and tight risk management."
    else:
        conviction = "LOW"
        recommendation = "Poor technical alignment. Consider waiting for better setup or alternative opportunities."
    
    analysis_insights["summary"] = {
        "conviction": conviction,
        "recommendation": recommendation,
        "key_levels": {
            "support": fibs["61%"],
            "resistance": fibs["38%"],
            "current_trend": "BULLISH" if indicators_data.get("MACD", 0) > 0 else "BEARISH"
        }
    }
    
    # Calculate relative strength analysis
    relative_strength = calculate_relative_strength(symbol, df)
    analysis_insights["relative_strength"] = relative_strength

    return {
      "symbol":     symbol.upper(),
      "price":      round(latest["Close"],2),
      "fib_levels": fibs,
      "indicators": indicators_data,
      "analysis":   analysis_insights,
      "timeseries": ts,
      "plan":       plan,
      "score":      clean_nan(score) or 0
    }
