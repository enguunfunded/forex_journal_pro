from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()
_SessionLocal = None

class Trade(Base):
    __tablename__ = "trade"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    direction = Column(String)
    entry_time = Column(DateTime)
    rr = Column(Float)
    session = Column(String)
    h4_dir = Column(String)
    h1_dir = Column(String)
    m15_dir = Column(String)
    mtf_score = Column(Integer)
    result = Column(String)
    notes = Column(Text)
    checklists = relationship("TradeChecklist", back_populates="trade")
    entry_price = Column(Float, nullable=True)
    sl_price    = Column(Float, nullable=True)
    exit_price  = Column(Float, nullable=True)

class ChecklistItem(Base):
    __tablename__ = "checklist_item"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    label = Column(String)

class TradeChecklist(Base):
    __tablename__ = "trade_checklist"
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trade.id"))
    item_id = Column(Integer, ForeignKey("checklist_item.id"))
    checked = Column(Boolean, default=True)
    trade = relationship("Trade", back_populates="checklists")
    item = relationship("ChecklistItem")

_ENGINE = None  # нэмэлт глобал хувьсагч

def init_db(db_path: str):
    global _SessionLocal, _ENGINE
    url = f"sqlite:///{db_path}"
    _ENGINE = create_engine(url, future=True)
    Base.metadata.create_all(_ENGINE)
    _SessionLocal = sessionmaker(bind=_ENGINE, future=True)

def get_session(db_path: str):
    return _SessionLocal()

def get_engine():
    """Pandas read_sql_query ашиглахад хэрэгтэй"""
    return _ENGINE

