import os, requests
from functools import lru_cache

API_KEY = os.getenv("POLYGON_API_KEY")

# Polygon index symbols
INDEX_SYMBOLS = {
    "nasdaq": "NDX",
    "sp500":  "SPX",
    "dow":    "DJI"
}

@lru_cache(maxsize=3)
def get_constituents(index_name: str):
    idx = INDEX_SYMBOLS.get(index_name.lower())
    if not idx:
        raise ValueError("Unknown index")
    url = (
      f"https://api.polygon.io/v3/reference/index_constituents"
      f"?symbol={idx}&apiKey={API_KEY}"
    )
    res = requests.get(url); res.raise_for_status()
    data = res.json()
    results = data.get("results", [])
    tickers = [r["ticker"] for r in results]
    # handle pagination
    next_url = data.get("next_url")
    while next_url:
        res = requests.get(next_url + f"&apiKey={API_KEY}")
        res.raise_for_status()
        data = res.json()
        tickers += [r["ticker"] for r in data.get("results", [])]
        next_url = data.get("next_url")
    return tickers

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
