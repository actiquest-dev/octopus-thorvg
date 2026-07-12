"""
Face Database Module
Управление профилями пользователей и сохранение face embeddings
Использует Redis для кэширования и in-memory граф для простоты

В production можно заменить на FalkorDB или PostgreSQL+pgvector
"""

import asyncio
import json
import uuid
import time
from typing import List, Optional, Dict, Tuple
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FaceDatabase:
    """
    Управление профилями пользователей и Face ID данными

    Структура в памяти:
    {
        "users": {
            "user_id": {
                "id": "user_id",
                "name": "John Doe",
                "created_at": timestamp,
                "last_seen": timestamp,
                "face_profiles": ["profile_id1", "profile_id2"],
                "interaction_count": 42,
                "profile_data": {...}  # Для Gemini долгую память
            }
        },
        "face_profiles": {
            "profile_id": {
                "id": "profile_id",
                "user_id": "user_id",
                "embedding": [float, ...],  # 128-dim
                "captured_at": timestamp,
                "quality_score": 0.95,
                "image_hash": "hash"
            }
        }
    }
    """

    def __init__(self):
        """Инициализировать базу данных"""
        self.users: Dict[str, Dict] = {}
        self.face_profiles: Dict[str, Dict] = {}
        self.embedding_index: Dict[str, List[str]] = {}  # Индекс для быстрого поиска
        logger.info("✅ FaceDatabase инициализирована (in-memory)")

    async def init(self):
        """Инициализировать БД (может загрузить из персистентного хранилища)"""
        logger.info("📊 FaceDatabase инициализирована и готова к работе")

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
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())

        now = time.time()

        # Создать профиль пользователя
        user = {
            "id": user_id,
            "name": name,
            "created_at": now,
            "last_seen": now,
            "face_profiles": [profile_id],
            "interaction_count": 0,
            "profile_data": profile_data or {},
            "emotions": [],
            "actions": [],
            "conversation_history": []
        }

        # Создать profile для лица
        face_profile = {
            "id": profile_id,
            "user_id": user_id,
            "embedding": embedding,
            "captured_at": now,
            "quality_score": 1.0,
            "image_hash": self._hash_embedding(embedding)
        }

        # Сохранить в БД
        self.users[user_id] = user
        self.face_profiles[profile_id] = face_profile

        logger.info(f"✅ Новый пользователь зарегистрирован: {name} (ID: {user_id})")

        return {
            "user_id": user_id,
            "name": name,
            "face_profile_id": profile_id,
            "status": "registered"
        }

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
        if not self.face_profiles:
            return None

        embedding_np = np.array(embedding, dtype=np.float32)
        best_match = None
        best_similarity = 0.0

        # Брутфорс поиск (в production использовать индексы)
        for profile_id, profile in self.face_profiles.items():
            stored_embedding = np.array(profile["embedding"], dtype=np.float32)

            # Нормализовать для cosine similarity
            stored_norm = np.linalg.norm(stored_embedding)
            query_norm = np.linalg.norm(embedding_np)

            if stored_norm == 0 or query_norm == 0:
                similarity = 0.0
            else:
                similarity = np.dot(embedding_np, stored_embedding) / (query_norm * stored_norm)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (profile_id, profile, similarity)

        if best_match and best_similarity >= threshold:
            profile_id, profile, similarity = best_match
            user = self.users[profile["user_id"]]

            # Обновить last_seen
            user["last_seen"] = time.time()
            user["interaction_count"] += 1

            logger.info(f"✅ Пользователь найден: {user['name']} (confidence: {similarity:.2f})")

            return {
                "user_id": user["id"],
                "name": user["name"],
                "confidence": float(similarity),
                "matched_profile_id": profile_id
            }

        logger.debug(f"❌ Пользователь не найден (best similarity: {best_similarity:.2f}, threshold: {threshold})")
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
        if user_id not in self.users:
            logger.warning(f"❌ Пользователь {user_id} не найден")
            return False

        user = self.users[user_id]

        # Обновить embeddings (усредн. с существующими)
        if new_embedding:
            profile_id = user["face_profiles"][0]  # Берём первый profile
            existing_profile = self.face_profiles[profile_id]

            # Усредняем embeddings для улучшения качества
            existing_emb = np.array(existing_profile["embedding"], dtype=np.float32)
            new_emb = np.array(new_embedding, dtype=np.float32)
            averaged = (existing_emb + new_emb) / 2

            existing_profile["embedding"] = averaged.tolist()
            existing_profile["quality_score"] = min(1.0, existing_profile["quality_score"] + 0.05)

            logger.debug(f"📊 Embeddings обновлены для {user['name']}")

        # Обновить доп. данные
        if profile_data_update:
            user["profile_data"].update(profile_data_update)
            logger.debug(f"📝 Профиль обновлён для {user['name']}")

        user["last_seen"] = time.time()
        return True

    async def get_user_history(self, user_id: str) -> Optional[Dict]:
        """
        Получить историю пользователя для персонализации

        Returns:
            {
                user_id,
                name,
                last_seen,
                interaction_count,
                average_emotion,
                average_action,
                profile_data,
                conversation_snippets
            }
        """
        if user_id not in self.users:
            return None

        user = self.users[user_id]

        # Вычислить статистику
        emotions = user.get("emotions", [])
        actions = user.get("actions", [])

        avg_emotion = None
        if emotions:
            # Найти наиболее частую эмоцию
            emotion_counts = {}
            for emotion in emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            avg_emotion = max(emotion_counts, key=emotion_counts.get)

        avg_action = None
        if actions:
            action_counts = {}
            for action in actions:
                action_counts[action] = action_counts.get(action, 0) + 1
            avg_action = max(action_counts, key=action_counts.get)

        return {
            "user_id": user["id"],
            "name": user["name"],
            "last_seen": user["last_seen"],
            "interaction_count": user["interaction_count"],
            "created_at": user["created_at"],
            "average_emotion": avg_emotion,
            "average_action": avg_action,
            "profile_data": user["profile_data"],
            "emotions_history": emotions[-10:],  # Последние 10
            "actions_history": actions[-10:],
            "conversation_history": user.get("conversation_history", [])[-5:]  # Последние 5
        }

    async def add_interaction(
        self,
        user_id: str,
        emotion: Optional[str] = None,
        action: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        Записать взаимодействие пользователя

        Args:
            user_id: ID пользователя
            emotion: Обнаруженная эмоция
            action: Совершённое действие
            message: Сообщение от пользователя

        Returns:
            True если успешно
        """
        if user_id not in self.users:
            return False

        user = self.users[user_id]

        if emotion:
            user["emotions"].append(emotion)
            # Ограничить историю до 100 последних
            user["emotions"] = user["emotions"][-100:]

        if action:
            user["actions"].append(action)
            user["actions"] = user["actions"][-100:]

        if message:
            user["conversation_history"].append({
                "timestamp": time.time(),
                "message": message
            })
            user["conversation_history"] = user["conversation_history"][-50:]

        user["last_seen"] = time.time()
        return True

    def _hash_embedding(self, embedding: List[float]) -> str:
        """Простой хэш embedding для дедупликации"""
        import hashlib
        embedding_str = ",".join(f"{x:.4f}" for x in embedding[:20])  # Первые 20 значений
        return hashlib.md5(embedding_str.encode()).hexdigest()[:16]

    async def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        return list(self.users.values())

    async def delete_user(self, user_id: str) -> bool:
        """Удалить пользователя и его данные"""
        if user_id not in self.users:
            return False

        user = self.users[user_id]

        # Удалить все face profiles
        for profile_id in user["face_profiles"]:
            if profile_id in self.face_profiles:
                del self.face_profiles[profile_id]

        # Удалить пользователя
        del self.users[user_id]

        logger.info(f"🗑️ Пользователь удалён: {user['name']} ({user_id})")
        return True

    def get_stats(self) -> Dict:
        """Получить статистику БД"""
        return {
            "total_users": len(self.users),
            "total_face_profiles": len(self.face_profiles),
            "total_interactions": sum(u["interaction_count"] for u in self.users.values()),
            "users_list": [
                {
                    "name": u["name"],
                    "last_seen": u["last_seen"],
                    "interactions": u["interaction_count"]
                }
                for u in self.users.values()
            ]
        }


# Глобальный экземпляр БД
_face_database: Optional[FaceDatabase] = None


async def get_face_database() -> FaceDatabase:
    """Получить глобальный экземпляр face database"""
    global _face_database
    if _face_database is None:
        _face_database = FaceDatabase()
        await _face_database.init()
    return _face_database


async def init_face_database():
    """Инициализировать face database"""
    db = await get_face_database()
    logger.info("✅ Face Database готова")
    return db
