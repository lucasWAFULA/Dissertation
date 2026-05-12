from __future__ import annotations
import pandas as pd
from sqlalchemy import create_engine, Column, Float, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from src.config import DATABASE_URL

Base = declarative_base()

class PriceRecord(Base):
    __tablename__ = "price_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    commodity = Column(String, nullable=False, index=True)
    county = Column(String, nullable=False, index=True)
    market = Column(String)
    price_real = Column(Float, nullable=False)
    record_type = Column(String, default="live")
    risk_score = Column(Float, default=0.0)
    severity = Column(String, default="Low")
    is_anomaly = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_prices_to_db(df: pd.DataFrame):
    """Save a dataframe of prices to the database."""
    df.to_sql("price_records", con=engine, if_exists="append", index=False)

def load_prices_from_db(limit: int = 1000) -> pd.DataFrame:
    """Load the latest price records from the database."""
    query = f"SELECT * FROM price_records ORDER BY date DESC LIMIT {limit}"
    return pd.read_sql(query, con=engine)
