from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./pv_local.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String) 
    role = Column(String) 

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    description = Column(String)
    book_qty = Column(Float, default=0.0)
    counts = relationship("PhysicalCount", back_populates="item")

class PhysicalCount(Base):
    __tablename__ = "physical_counts"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    auditor_name = Column(String)
    qty = Column(Float)
    item = relationship("Item", back_populates="counts")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).first():
        db.add(User(username="admin", password="123", role="admin"))
        db.add(User(username="auditor", password="123", role="auditor"))
        db.commit()
    db.close()
