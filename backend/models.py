from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date
import json
import hashlib

class Recommendation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    symbol: str
    score: float
    analysis_data: str = Field(default="{}")

class WatchlistItem(SQLModel, table=True):
    symbol: str = Field(primary_key=True)

class PortfolioPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    entry_date: date
    entry_price: float
    quantity: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED, STOPPED_OUT
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    notes: Optional[str] = None
    ibkr_account_id: Optional[str] = Field(default=None, index=True)
    ibkr_con_id: Optional[int] = Field(default=None, index=True)
    sec_type: Optional[str] = Field(default="STK")
    currency: Optional[str] = Field(default="USD")
    exchange: Optional[str] = Field(default=None)

class ScreenerCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(unique=True)  # Hash of filter parameters
    filters_json: str  # JSON string of the original filters
    results_json: str  # JSON string of the screening results
    created_date: date
    result_count: int
    
    @classmethod
    def generate_cache_key(cls, filters: dict) -> str:
        """Generate a unique cache key based on filter parameters"""
        # Normalize filters for consistent hashing
        normalized = {
            'min_price': filters.get('min_price', 1),
            'max_price': filters.get('max_price', 1000),
            'min_volume': filters.get('min_volume', 10000),
            'min_market_cap': filters.get('min_market_cap', 10000000),
            'max_market_cap': filters.get('max_market_cap'),
            'patterns': sorted(filters.get('patterns', []))  # Sort for consistency
        }
        
        # Create hash from normalized filters
        filter_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(filter_str.encode()).hexdigest()

class TradingPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_name: str
    total_capital: float
    risk_percentage: float = 2.0  # Default 2% risk per position
    max_positions: int = 5  # Maximum number of positions
    filters_json: str  # JSON string of screening filters used
    created_date: date
    plan_data: str  # JSON string containing the complete plan
    
    # Plan status
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED
    
    @classmethod
    def calculate_position_sizing(cls, capital: float, risk_pct: float, entry_price: float, stop_loss: float) -> dict:
        """Calculate position size based on risk management"""
        risk_amount = capital * (risk_pct / 100)
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return {"shares": 0, "position_value": 0, "risk_amount": 0}
            
        shares = int(risk_amount / price_risk)
        position_value = shares * entry_price
        
        return {
            "shares": shares,
            "position_value": round(position_value, 2),
            "risk_amount": round(risk_amount, 2),
            "price_risk": round(price_risk, 2)
        }

# Alerts will simply mirror latest Recommendations for simplicity
