import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Default to MySQL for containerized deployment; override with DATABASE_URL env var as needed
# Example: mysql+pymysql://app:app@mysql:3306/fasanua
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://app:app@mysql:3306/fasanua")

engine = create_engine(
  DATABASE_URL,
  connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
  pass




