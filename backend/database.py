"""
Database configuration и подключения
PostgreSQL для основных данных + Redis для кэша
"""

import os
import asyncio
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from loguru import logger
import json

# Конфигурация из .env
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "face_id_db")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# PostgreSQL async engine
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"timeout": 10}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis() -> Optional[redis.Redis]:
    """Инициализировать Redis подключение"""
    global redis_client
    try:
        redis_client = await redis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=2,
            retry_on_timeout=True
        )
        await redis_client.ping()
        logger.info(f"✅ Redis подключен: {REDIS_HOST}:{REDIS_PORT}")
        return redis_client
    except Exception as e:
        logger.warning(f"⚠️ Redis не найден, используем локальный кэш: {e}")
        redis_client = None
        return None


async def close_redis():
    """Закрыть Redis подключение"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("✅ Redis отключен")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения БД сессии"""
    async with AsyncSessionLocal() as session:
        yield session


class RedisCache:
    """Кэширование на Redis (с фолбеком на локальный dict)"""

    _local_storage = {}

    def __init__(self, redis_conn: Optional[redis.Redis]):
        self.redis = redis_conn

    async def get(self, key: str) -> Optional[dict]:
        """Получить из кэша"""
        try:
            if self.redis:
                data = await self.redis.get(key)
                if data:
                    return json.loads(data)
            else:
                return self._local_storage.get(key)
        except Exception as e:
            logger.warning(f"❌ Cache get ошибка {key}: {e}")
        return None

    async def set(self, key: str, value: dict, ttl: int = 3600) -> bool:
        """Сохранить в кэш"""
        try:
            if self.redis:
                await self.redis.setex(key, ttl, json.dumps(value))
            else:
                self._local_storage[key] = value
            return True
        except Exception as e:
            logger.warning(f"❌ Cache set ошибка {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Удалить из кэша"""
        try:
            if self.redis:
                await self.redis.delete(key)
            else:
                self._local_storage.pop(key, None)
            return True
        except Exception as e:
            logger.warning(f"❌ Cache delete ошибка {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Удалить все ключи по паттерну"""
        try:
            if self.redis:
                keys = await self.redis.keys(pattern)
                if keys:
                    return await self.redis.delete(*keys)
            else:
                import fnmatch
                to_delete = [k for k in self._local_storage.keys() if fnmatch.fnmatch(k, pattern)]
                for k in to_delete:
                    del self._local_storage[k]
                return len(to_delete)
            return 0
        except Exception as e:
            logger.warning(f"❌ Cache clear_pattern ошибка {pattern}: {e}")
            return 0

    async def store_embedding(self, user_id: str, embedding: list[float], ttl: int = 86400*30):
        """Сохранить embedding вектор лица"""
        key = f"face:embedding:{user_id}"
        await self.set(key, {"embedding": embedding}, ttl)

    async def get_embedding(self, user_id: str) -> Optional[list[float]]:
        """Получить embedding вектор лица"""
        data = await self.get(f"face:embedding:{user_id}")
        if data:
            return data.get("embedding")
        return None


async def init_db():
    """Инициализировать БД"""
    try:
        async with engine.begin() as conn:
            # Импортировать все модели для автосоздания таблиц
            from models import Base
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ PostgreSQL таблицы созданы")
    except Exception as e:
        logger.error(f"❌ PostgreSQL инициализация ошибка: {e}")
        raise


async def close_db():
    """Закрыть БД подключение"""
    await engine.dispose()
    logger.info("✅ PostgreSQL отключен")
