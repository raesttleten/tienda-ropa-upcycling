from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ------------------------------------------------------------------
# 🔹 SI ESTÁS LOCAL → usa SQLite
# 🔹 SI ESTÁS EN RAILWAY → usa PostgreSQL automáticamente
# ------------------------------------------------------------------

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tienda_upcycling.db")

# Configuración especial para SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # Railway usa PostgreSQL → no necesita check_same_thread
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# -------------------------------
# Dependencia para FastAPI
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
