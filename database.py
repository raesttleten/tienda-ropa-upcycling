from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://postgres:fTSmOBCrZKvkfjOVAPQsocIvJwehbUhO@gondola.proxy.rlwy.net:47968/railway"

# Engine async
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base declarativa
Base = declarative_base()

# Dependencia para endpoints
async def get_db():
    async with SessionLocal() as session:
        yield session

# Crear tablas de forma async
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
