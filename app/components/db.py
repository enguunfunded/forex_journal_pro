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

def init_db(db_path: str):
    global _SessionLocal
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    _SessionLocal = sessionmaker(bind=engine, future=True)

def get_session(db_path: str):
    return _SessionLocal()
