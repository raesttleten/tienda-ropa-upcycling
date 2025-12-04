import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# Obtener DATABASE_URL de variable de entorno (Railway la provee automáticamente)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:fTSmOBCrZKvkfjOVAPQsocIvJwehbUhO@gondola.proxy.rlwy.net:47968/railway"
)

# Railway a veces provee URLs con postgres:// en lugar de postgresql://
# Necesitamos convertirlo para asyncpg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    logger.info("✓ URL de base de datos convertida para asyncpg")

logger.info(f"📊 Conectando a base de datos: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")

# Engine async con configuraciones de producción
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # False en producción para reducir logs
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_size=5,  # Tamaño del pool de conexiones
    max_overflow=10,  # Conexiones adicionales permitidas
    pool_recycle=3600,  # Reciclar conexiones cada hora
)

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
        try:
            yield session
        except Exception as e:
            logger.error(f"❌ Error en sesión de base de datos: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Crear tablas de forma async
async def init_models():
    try:
        logger.info("🔄 Intentando crear tablas en la base de datos...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tablas creadas/verificadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error al crear tablas: {e}")
        raise