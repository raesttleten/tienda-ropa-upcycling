from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

import os


DATABASE_URL = "postgresql+asyncpg://postgres:fTSmOBCrZKvkfjOVAPQsocIvJwehbUhO@gondola.proxy.rlwy.net:47968/railway"

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session


