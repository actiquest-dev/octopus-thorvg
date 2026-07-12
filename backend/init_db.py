"""
Инициализация PostgreSQL базы данных для Face ID системы
Создаёт таблицы, индексы и включает pgvector расширение
"""

import asyncio
import os
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from loguru import logger


def create_database_sync():
    """Создать БД синхронно (CREATE DATABASE требует autocommit)"""
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "face_id_db")

    # Синхронное подключение к postgres БД
    postgres_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"

    engine = create_engine(postgres_url, echo=False, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        # Проверить и создать БД если её нет
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{POSTGRES_DB}'")
        )
        exists = result.fetchone()

        if not exists:
            conn.execute(text(f"CREATE DATABASE {POSTGRES_DB}"))
            logger.info(f"✅ База данных '{POSTGRES_DB}' создана")
        else:
            logger.info(f"✅ База данных '{POSTGRES_DB}' уже существует")

    engine.dispose()


async def enable_pgvector():
    """Включить pgvector расширение"""
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "face_id_db")

    face_db_url = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    engine = create_async_engine(face_db_url, echo=False)

    try:
        async with engine.connect() as conn:
            # Попытка включить pgvector
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.commit()
                logger.info("✅ pgvector расширение активировано")
                return True
            except Exception as e:
                logger.warning(f"⚠️ pgvector не удалось активировать: {e}")
                return False
    finally:
        await engine.dispose()


async def init_postgres_db():
    """Инициализировать PostgreSQL таблицы для Face ID"""

    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "face_id_db")

    # Async подключение к face_id_db
    face_db_url = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    engine = create_async_engine(face_db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Создать таблицу users
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    interaction_count INTEGER DEFAULT 0,
                    profile_data JSONB DEFAULT '{}'::jsonb,
                    emotions JSONB DEFAULT '[]'::jsonb,
                    actions JSONB DEFAULT '[]'::jsonb,
                    conversation_history JSONB DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("✅ Таблица 'users' создана/проверена")

            # Создать таблицу face_profiles с обычным массивом вместо vector
            # (если pgvector не установлен, будем использовать FLOAT8[] для embeddings)
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS face_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    embedding FLOAT8[] NOT NULL,
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quality_score FLOAT DEFAULT 1.0 CHECK (quality_score >= 0 AND quality_score <= 1),
                    image_hash VARCHAR(32),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("✅ Таблица 'face_profiles' создана/проверена")

            # Индекс по user_id
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_face_user_id
                    ON face_profiles(user_id)
                """))
            except:
                pass

            # Индекс по created_at для сортировки
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_face_created_at
                    ON face_profiles(created_at DESC)
                """))
            except:
                pass

            logger.info("✅ Все индексы созданы/проверены")

            # Создать таблицу для интеграции с Gemini
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gemini_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    conversation_context JSONB,
                    detected_emotions JSONB DEFAULT '[]'::jsonb,
                    detected_actions JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("✅ Таблица 'gemini_sessions' создана/проверена")

    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации таблиц: {e}")
        raise

    finally:
        await engine.dispose()

    logger.info("✅ PostgreSQL инициализация таблиц завершена успешно")


async def test_connection():
    """Протестировать подключение к БД"""
    from database import engine

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ PostgreSQL подключение работает")

            # Проверить pgvector
            result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            vec_version = result.fetchone()
            if vec_version:
                logger.info(f"✅ pgvector версия: {vec_version[0]}")
            else:
                logger.warning("⚠️ pgvector расширение не установлено (используем FLOAT8[] для embeddings)")

            return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        return False


if __name__ == "__main__":
    # Сначала создать БД синхронно
    create_database_sync()

    # Попытка активировать pgvector
    asyncio.run(enable_pgvector())

    # Затем инициализировать таблицы асинхронно
    asyncio.run(init_postgres_db())
    asyncio.run(test_connection())
