from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

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

# Alerts will simply mirror latest Recommendations for simplicity
