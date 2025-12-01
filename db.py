import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_env_database_url = (os.getenv("DATABASE_URL") or "").strip()
SSL_CA = os.getenv("MYSQL_SSL_CA") or os.getenv("DB_SSL_CA")

connect_args = {}
if not _env_database_url:
    # Fallback to SQLite. Prefer persisted path on Azure App Service.
    azure_wwwroot = "/home/site/wwwroot"
    base_dir = azure_wwwroot if os.path.isdir(azure_wwwroot) else "."
    db_dir = os.path.join(base_dir, "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "app.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    connect_args = {"check_same_thread": False}
else:
    DATABASE_URL = _env_database_url

if DATABASE_URL.startswith("sqlite"):
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




