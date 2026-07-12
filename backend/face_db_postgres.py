"""
Face Database Module - PostgreSQL Version
Управление профилями пользователей и сохранение face embeddings
Использует PostgreSQL + Redis кэш для оптимальной производительности
"""

import asyncio
import json
import uuid
import time
from typing import List, Optional, Dict
import numpy as np
from loguru import logger
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, redis_client
from datetime import datetime


class FaceDatabasePostgres:
    """
    Управление профилями пользователей и Face ID данными в PostgreSQL
    """

    def __init__(self):
        logger.info("✅ FaceDatabase (PostgreSQL) инициализирована")

    async def init(self):
        """Инициализировать БД"""
        logger.info("📊 FaceDatabase (PostgreSQL) готова к работе")

    async def register_new_user(
        self,
        name: str,
        embedding: List[float],
        profile_data: Optional[Dict] = None
    ) -> Dict:
        """
        Зарегистрировать новое пользователя

        Args:
            name: Имя пользователя
            embedding: Face embedding (вектор)
            profile_data: Доп. данные профиля (для Gemini)

        Returns:
            {user_id, name, face_profile_id, status}
        """
        async with AsyncSessionLocal() as session:
            try:
                user_id = str(uuid.uuid4())
                profile_id = str(uuid.uuid4())
                now = datetime.utcnow()

                # Создать пользователя
                await session.execute(text("""
                    INSERT INTO users (id, name, created_at, last_seen, interaction_count, profile_data)
                    VALUES (:id, :name, :created_at, :last_seen, :interaction_count, :profile_data)
                """), {
                    "id": user_id,
                    "name": name,
                    "created_at": now,
                    "last_seen": now,
                    "interaction_count": 0,
                    "profile_data": json.dumps(profile_data or {})
                })

                # Создать face profile
                embedding_array = f"ARRAY[{','.join(str(e) for e in embedding)}]"
                await session.execute(text(f"""
                    INSERT INTO face_profiles (id, user_id, embedding, captured_at, quality_score, image_hash)
                    VALUES (:id, :user_id, {embedding_array}, :captured_at, :quality_score, :image_hash)
                """), {
                    "id": profile_id,
                    "user_id": user_id,
                    "captured_at": now,
                    "quality_score": 1.0,
                    "image_hash": self._hash_embedding(embedding)
                })

                await session.commit()

                # Кэшировать в Redis
                if redis_client:
                    cache_key = f"face:user:{user_id}"
                    await redis_client.setex(
                        cache_key,
                        86400,  # 24 часа
                        json.dumps({
                            "user_id": user_id,
                            "name": name,
                            "face_profile_id": profile_id
                        })
                    )

                logger.info(f"✅ Новый пользователь зарегистрирован: {name} (ID: {user_id})")

                return {
                    "user_id": user_id,
                    "name": name,
                    "face_profile_id": profile_id,
                    "status": "registered"
                }

            except Exception as e:
                logger.error(f"❌ Ошибка регистрации пользователя: {e}")
                raise

    async def find_user_by_face(
        self,
        embedding: List[float],
        threshold: float = 0.6
    ) -> Optional[Dict]:
        """
        Найти пользователя по face embedding

        Args:
            embedding: Новый embedding для поиска
            threshold: Минимальный cosine similarity (0-1)

        Returns:
            {user_id, name, confidence, matched_profile_id} или None
        """
        async with AsyncSessionLocal() as session:
            try:
                # Получить все embeddings
                result = await session.execute(text("""
                    SELECT id, user_id, embedding FROM face_profiles ORDER BY created_at DESC LIMIT 1000
                """))

                embedding_np = np.array(embedding, dtype=np.float32)
                best_match = None
                best_similarity = 0.0

                for row in result:
                    profile_id, user_id, stored_embedding = row
                    stored_array = np.array(stored_embedding, dtype=np.float32)

                    # Нормализовать для cosine similarity
                    stored_norm = np.linalg.norm(stored_array)
                    query_norm = np.linalg.norm(embedding_np)

                    if stored_norm == 0 or query_norm == 0:
                        similarity = 0.0
                    else:
                        similarity = float(np.dot(embedding_np, stored_array) / (query_norm * stored_norm))

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = (profile_id, user_id, similarity)

                if best_match and best_similarity >= threshold:
                    profile_id, user_id, similarity = best_match

                    # Получить пользователя
                    user_result = await session.execute(text("""
                        SELECT id, name FROM users WHERE id = :user_id
                    """), {"user_id": user_id})

                    user_row = user_result.fetchone()
                    if not user_row:
                        return None

                    user_id, user_name = user_row

                    # Обновить last_seen и interaction_count
                    await session.execute(text("""
                        UPDATE users
                        SET last_seen = :now, interaction_count = interaction_count + 1
                        WHERE id = :user_id
                    """), {"now": datetime.utcnow(), "user_id": user_id})

                    await session.commit()

                    logger.info(f"✅ Пользователь найден: {user_name} (confidence: {similarity:.2f})")

                    return {
                        "user_id": str(user_id),
                        "name": user_name,
                        "confidence": similarity,
                        "matched_profile_id": str(profile_id)
                    }

                logger.debug(f"❌ Пользователь не найден (best similarity: {best_similarity:.2f}, threshold: {threshold})")
                return None

            except Exception as e:
                logger.error(f"❌ Ошибка поиска пользователя: {e}")
                return None

    async def update_user_profile(
        self,
        user_id: str,
        new_embedding: Optional[List[float]] = None,
        profile_data_update: Optional[Dict] = None
    ) -> bool:
        """
        Обновить профиль пользователя

        Args:
            user_id: ID пользователя
            new_embedding: Новый embedding (усреднить с существующими)
            profile_data_update: Обновить доп. данные

        Returns:
            True если успешно
        """
        async with AsyncSessionLocal() as session:
            try:
                # Проверить существование пользователя
                user_result = await session.execute(text("""
                    SELECT id FROM users WHERE id = :user_id
                """), {"user_id": user_id})

                if not user_result.fetchone():
                    logger.warning(f"❌ Пользователь {user_id} не найден")
                    return False

                # Обновить embeddings (усреднение)
                if new_embedding:
                    # Получить последний embedding
                    profile_result = await session.execute(text("""
                        SELECT id, embedding FROM face_profiles
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    """), {"user_id": user_id})

                    profile_row = profile_result.fetchone()
                    if profile_row:
                        profile_id, existing_emb = profile_row
                        existing_array = np.array(existing_emb, dtype=np.float32)
                        new_array = np.array(new_embedding, dtype=np.float32)
                        averaged = (existing_array + new_array) / 2

                        embedding_array = f"ARRAY[{','.join(str(e) for e in averaged)}]"
                        await session.execute(text(f"""
                            UPDATE face_profiles
                            SET embedding = {embedding_array}, quality_score = MIN(1.0, quality_score + 0.05)
                            WHERE id = :profile_id
                        """), {"profile_id": profile_id})

                        logger.debug(f"📊 Embeddings обновлены для {user_id}")

                # Обновить доп. данные
                if profile_data_update:
                    await session.execute(text("""
                        UPDATE users
                        SET profile_data = profile_data || :update
                        WHERE id = :user_id
                    """), {
                        "update": json.dumps(profile_data_update),
                        "user_id": user_id
                    })

                    logger.debug(f"📝 Профиль обновлён для {user_id}")

                await session.execute(text("""
                    UPDATE users SET last_seen = :now WHERE id = :user_id
                """), {"now": datetime.utcnow(), "user_id": user_id})

                await session.commit()
                return True

            except Exception as e:
                logger.error(f"❌ Ошибка обновления профиля: {e}")
                return False

    async def get_user_history(self, user_id: str) -> Optional[Dict]:
        """Получить историю пользователя для персонализации"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(text("""
                    SELECT
                        id, name, last_seen, interaction_count, created_at,
                        emotions, actions, conversation_history, profile_data
                    FROM users
                    WHERE id = :user_id
                """), {"user_id": user_id})

                row = result.fetchone()
                if not row:
                    return None

                user_id, name, last_seen, interaction_count, created_at, emotions, actions, conv_history, profile_data = row

                # Парсить JSON (asyncpg возвращает JSONB уже как Python-объекты)
                def _as_list(val):
                    if not val:
                        return []
                    return val if isinstance(val, list) else json.loads(val)

                emotions_list = _as_list(emotions)
                actions_list = _as_list(actions)
                conv_list = _as_list(conv_history)

                # Вычислить статистику
                avg_emotion = None
                if emotions_list:
                    emotion_counts = {}
                    for emotion in emotions_list:
                        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                    avg_emotion = max(emotion_counts, key=emotion_counts.get)

                avg_action = None
                if actions_list:
                    action_counts = {}
                    for action in actions_list:
                        action_counts[action] = action_counts.get(action, 0) + 1
                    avg_action = max(action_counts, key=action_counts.get)

                return {
                    "user_id": str(user_id),
                    "name": name,
                    "last_seen": last_seen.isoformat() if last_seen else None,
                    "interaction_count": interaction_count,
                    "created_at": created_at.isoformat() if created_at else None,
                    "average_emotion": avg_emotion,
                    "average_action": avg_action,
                    "profile_data": profile_data if isinstance(profile_data, dict) else (json.loads(profile_data) if profile_data else {}),
                    "emotions_history": emotions_list[-10:],
                    "actions_history": actions_list[-10:],
                    "conversation_history": conv_list[-5:]
                }

            except Exception as e:
                logger.error(f"❌ Ошибка получения истории: {e}")
                return None

    async def add_interaction(
        self,
        user_id: str,
        emotion: Optional[str] = None,
        action: Optional[str] = None,
        message: Optional[str] = None,
        speaker: Optional[str] = None
    ) -> bool:
        """Записать взаимодействие пользователя"""
        async with AsyncSessionLocal() as session:
            try:
                if emotion:
                    await session.execute(text("""
                        UPDATE users
                        SET emotions = emotions || :emotion
                        WHERE id = :user_id
                    """), {
                        "emotion": json.dumps([emotion]),
                        "user_id": user_id
                    })

                if action:
                    await session.execute(text("""
                        UPDATE users
                        SET actions = actions || :action
                        WHERE id = :user_id
                    """), {
                        "action": json.dumps([action]),
                        "user_id": user_id
                    })

                if message:
                    # Include speaker info if provided
                    msg_record = {
                        "timestamp": time.time(),
                        "message": message
                    }
                    if speaker:
                        msg_record["speaker"] = speaker

                    await session.execute(text("""
                        UPDATE users
                        SET conversation_history = conversation_history || :msg
                        WHERE id = :user_id
                    """), {
                        "msg": json.dumps([msg_record]),
                        "user_id": user_id
                    })

                await session.execute(text("""
                    UPDATE users SET last_seen = :now WHERE id = :user_id
                """), {"now": datetime.utcnow(), "user_id": user_id})

                await session.commit()
                return True

            except Exception as e:
                logger.error(f"❌ Ошибка добавления взаимодействия: {e}")
                return False

    def _hash_embedding(self, embedding: List[float]) -> str:
        """Простой хэш embedding для дедупликации"""
        import hashlib
        embedding_str = ",".join(f"{x:.4f}" for x in embedding[:20])
        return hashlib.md5(embedding_str.encode()).hexdigest()[:16]

    async def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(text("""
                    SELECT id, name, interaction_count, last_seen FROM users ORDER BY last_seen DESC
                """))

                users = []
                for row in result:
                    user_id, name, interaction_count, last_seen = row
                    users.append({
                        "id": str(user_id),
                        "name": name,
                        "interaction_count": interaction_count,
                        "last_seen": last_seen.isoformat() if last_seen else None
                    })

                return users

            except Exception as e:
                logger.error(f"❌ Ошибка получения пользователей: {e}")
                return []

    async def delete_user(self, user_id: str) -> bool:
        """Удалить пользователя и его данные"""
        async with AsyncSessionLocal() as session:
            try:
                # Face profiles удалятся автоматически через ON DELETE CASCADE
                result = await session.execute(text("""
                    DELETE FROM users WHERE id = :user_id RETURNING name
                """), {"user_id": user_id})

                deleted = result.fetchone()
                if deleted:
                    await session.commit()
                    logger.info(f"🗑️ Пользователь удалён: {deleted[0]} ({user_id})")
                    return True

                logger.warning(f"❌ Пользователь {user_id} не найден")
                return False

            except Exception as e:
                logger.error(f"❌ Ошибка удаления пользователя: {e}")
                return False

    async def get_stats(self) -> Dict:
        """Получить статистику БД"""
        async with AsyncSessionLocal() as session:
            try:
                users_result = await session.execute(text("SELECT COUNT(*) FROM users"))
                total_users = users_result.scalar() or 0

                profiles_result = await session.execute(text("SELECT COUNT(*) FROM face_profiles"))
                total_profiles = profiles_result.scalar() or 0

                interactions_result = await session.execute(text("SELECT SUM(interaction_count) FROM users"))
                total_interactions = interactions_result.scalar() or 0

                users_list_result = await session.execute(text("""
                    SELECT name, last_seen, interaction_count FROM users ORDER BY last_seen DESC
                """))

                users_list = [
                    {
                        "name": row[0],
                        "last_seen": row[1].isoformat() if row[1] else None,
                        "interactions": row[2]
                    }
                    for row in users_list_result
                ]

                return {
                    "total_users": total_users,
                    "total_face_profiles": total_profiles,
                    "total_interactions": total_interactions,
                    "users_list": users_list
                }

            except Exception as e:
                logger.error(f"❌ Ошибка получения статистики: {e}")
                return {
                    "total_users": 0,
                    "total_face_profiles": 0,
                    "total_interactions": 0,
                    "users_list": []
                }


# Глобальный экземпляр БД
_face_database: Optional[FaceDatabasePostgres] = None


async def get_face_database() -> FaceDatabasePostgres:
    """Получить глобальный экземпляр face database"""
    global _face_database
    if _face_database is None:
        _face_database = FaceDatabasePostgres()
        await _face_database.init()
    return _face_database


async def init_face_database():
    """Инициализировать face database"""
    db = await get_face_database()
    logger.info("✅ Face Database (PostgreSQL) готова")
    return db
