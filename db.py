import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")
SSL_CA = os.getenv("MYSQL_SSL_CA") or os.getenv("DB_SSL_CA")

connect_args = {}
if not DATABASE_URL:
    # Local/dev fallback to SQLite
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite:///./data/app.db"
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("mysql+pymysql://"):
    if SSL_CA:
        connect_args = {"ssl": {"ca": SSL_CA}}
    elif "mysql.database.azure.com" in DATABASE_URL:
        # Enable TLS by default for Azure MySQL if no CA provided
        connect_args = {"ssl": {}}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # important for Azure
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

class Base(DeclarativeBase):
    pass




