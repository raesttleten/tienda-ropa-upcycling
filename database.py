import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# Obtener URL de la base de datos desde la variable de entorno
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./local_dev.db"
)

# Normalizar URL para usar asyncpg con SQLAlchemy cuando venga de Railway o HEROKU
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info("DB URL normalizada (host enmascarado)")

# Crear engine y sessionmaker async
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """Dependency: yield una sesión AsyncSession"""
    async with AsyncSessionLocal() as session:
        yield session

async def init_models():
    """Crear tablas si no existen. Importar modelos aquí para evitar ciclos."""
    try:
        # import dentro de la función para evitar import cycles
        from models import Base as ModelsBase
        async with engine.begin() as conn:
            await conn.run_sync(ModelsBase.metadata.create_all)
        logger.info("✓ Tablas creadas/confirmadas en la DB")
    except Exception as e:
        logger.exception("Error inicializando modelos DB")
        raise
