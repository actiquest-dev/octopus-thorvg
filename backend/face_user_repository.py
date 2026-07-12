"""
Face User Repository
Работа с пользователями и их face profiles в PostgreSQL
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger
from datetime import datetime
from typing import Optional, List, Tuple

from models import User, FaceProfile
from database import RedisCache


class FaceUserRepository:
    """Репозиторий для работы с пользователями и лицами"""

    def __init__(self, db_session: AsyncSession, redis_cache: Optional[RedisCache] = None):
        self.db = db_session
        self.cache = redis_cache

    async def create_user(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        profile_data: Optional[dict] = None
    ) -> User:
        """Создать новое пользователя"""
        try:
            user = User(
                name=name,
                email=email,
                phone=phone,
                profile_data=profile_data or {}
            )
            self.db.add(user)
            await self.db.flush()
            logger.info(f"✅ Пользователь создан: {user.id}")
            return user
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        try:
            # Проверить кэш
            if self.cache:
                cached = await self.cache.get(f"user:{user_id}")
                if cached:
                    logger.info(f"💾 Пользователь получен из кэша: {user_id}")
                    return cached

            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user and self.cache:
                await self.cache.set(f"user:{user_id}", user.to_dict(), ttl=3600)

            return user
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        try:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя по email: {e}")
            return None

    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Обновить данные пользователя"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.last_seen = datetime.utcnow()
            await self.db.flush()

            # Обновить кэш
            if self.cache:
                await self.cache.delete(f"user:{user_id}")

            logger.info(f"✅ Пользователь обновлён: {user_id}")
            return user
        except Exception as e:
            logger.error(f"❌ Ошибка обновления пользователя: {e}")
            raise

    async def add_face_profile(
        self,
        user_id: str,
        embedding: List[float],
        quality_score: float = 0.0,
        image_data: Optional[bytes] = None,
        image_hash: Optional[str] = None,
        confidence: float = 0.0
    ) -> FaceProfile:
        """Добавить профиль лица пользователю"""
        try:
            face_profile = FaceProfile(
                user_id=user_id,
                embedding=embedding,
                quality_score=quality_score,
                image_data=image_data,
                image_hash=image_hash,
                confidence=confidence
            )
            self.db.add(face_profile)
            await self.db.flush()

            # Обновить кэш пользователя
            if self.cache:
                await self.cache.store_embedding(user_id, embedding)

            logger.info(f"✅ Face profile добавлен: {face_profile.id}")
            return face_profile
        except Exception as e:
            logger.error(f"❌ Ошибка добавления face profile: {e}")
            raise

    async def get_face_profiles(self, user_id: str) -> List[FaceProfile]:
        """Получить все face profiles пользователя"""
        try:
            result = await self.db.execute(
                select(FaceProfile).where(FaceProfile.user_id == user_id)
            )
            profiles = result.scalars().all()
            logger.info(f"📊 Получено {len(profiles)} face profiles для {user_id}")
            return profiles
        except Exception as e:
            logger.error(f"❌ Ошибка получения face profiles: {e}")
            return []

    async def get_all_face_embeddings(self) -> List[Tuple[str, List[float]]]:
        """Получить все embeddings всех пользователей для сравнения"""
        try:
            result = await self.db.execute(
                select(FaceProfile.user_id, FaceProfile.embedding)
            )
            rows = result.all()
            embeddings = [(user_id, emb) for user_id, emb in rows]
            logger.info(f"📊 Получено {len(embeddings)} embeddings для сравнения")
            return embeddings
        except Exception as e:
            logger.error(f"❌ Ошибка получения embeddings: {e}")
            return []

    async def get_active_users(self) -> List[User]:
        """Получить всех активных пользователей"""
        try:
            result = await self.db.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()
            logger.info(f"📊 Получено {len(users)} активных пользователей")
            return users
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных пользователей: {e}")
            return []

    async def increment_interaction_count(self, user_id: str) -> Optional[int]:
        """Увеличить счётчик взаимодействий"""
        try:
            user = await self.get_user_by_id(user_id)
            if user:
                user.interaction_count += 1
                await self.db.flush()
                logger.info(f"📈 Счётчик взаимодействий: {user_id} = {user.interaction_count}")
                return user.interaction_count
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка увеличения счётчика: {e}")
            return None

    async def deactivate_user(self, user_id: str) -> bool:
        """Деактивировать пользователя"""
        try:
            await self.update_user(user_id, is_active=False)
            logger.info(f"✅ Пользователь деактивирован: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации: {e}")
            return False

    async def commit(self):
        """Сохранить изменения в БД"""
        try:
            await self.db.commit()
            logger.info("✅ Изменения сохранены в БД")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Ошибка сохранения в БД: {e}")
            raise

    async def rollback(self):
        """Откатить изменения"""
        try:
            await self.db.rollback()
            logger.info("⏮️ Изменения откачены")
        except Exception as e:
            logger.error(f"❌ Ошибка отката: {e}")
