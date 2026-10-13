
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

user = quote_plus(os.getenv("DB_USER", "root"))
password = quote_plus(os.getenv("DB_PASSWORD", ""))
host = os.getenv("DB_HOST", "127.0.0.1")
port = os.getenv("DB_PORT", "3306")
name = os.getenv("DB_NAME", "move360_db")

DATABASE_URL = (
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    "?charset=utf8mb4"
)

# Aiven requires an encrypted database connection.
# Local XAMPP does not require SSL.
connect_args = {}

if os.getenv("DB_SSL", "false").lower() == "true":
    connect_args["ssl"] = {"check_hostname": True}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
