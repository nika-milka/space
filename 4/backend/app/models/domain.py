from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import pytz

Base = declarative_base()

class ISSPosition(Base):
    __tablename__ = "iss_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    velocity = Column(Float)
    visibility = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))

class NASADataset(Base):
    __tablename__ = "nasa_datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(Text)
    mission = Column(String)
    instrument = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    data_type = Column(String)
    file_size_mb = Column(Float)
    is_processed = Column(Boolean, default=False)
    raw_data = Column(Text)  # JSON как текст
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(pytz.UTC))

class APOD(Base):
    __tablename__ = "apod"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True)
    title = Column(String)
    explanation = Column(Text)
    url = Column(String)
    hdurl = Column(String)
    media_type = Column(String)
    copyright = Column(String, nullable=True)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))