from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Part:
    part_code: str
    name: str
    price_eur: float
    last_updated: datetime
    
@dataclass
class PriceHistory:
    part_code: str
    price_eur: float
    price_try: float
    exchange_rate: float
    date: datetime
    
@dataclass
class SearchHistory:
    id: int
    part_code: str
    search_date: datetime
    user: str
    
@dataclass
class User:
    username: str
    password_hash: str
    last_login: Optional[datetime] = None
