import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Default to MySQL for containerized deployment; override with DATABASE_URL env var as needed
# Example: mysql+pymysql://root:password@mysql:3306/fasanua
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:cielawid@mysql:3306/fasanua")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
  connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("mysql+pymysql://") and "mysql.database.azure.com" in DATABASE_URL:
  # Enable TLS for Azure MySQL. Provide ssl_ca in production for verification.
  connect_args = {"ssl": {}}

engine = create_engine(
  DATABASE_URL,
  connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
  pass




