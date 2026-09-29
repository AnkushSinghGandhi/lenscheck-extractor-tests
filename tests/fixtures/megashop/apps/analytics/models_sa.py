"""SQLAlchemy declarative models — a different ORM. `__tablename__` is the table."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True)
    email = Column(String)          # PII


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
