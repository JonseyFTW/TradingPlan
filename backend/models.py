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

# Alerts will simply mirror latest Recommendations for simplicity
