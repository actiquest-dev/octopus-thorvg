"""
Gemini Memory Management Module - PostgreSQL Version
Управление долгой памятью пользователя через Gemini API и PostgreSQL
"""

import asyncio
import json
import time
from loguru import logger
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from face_db_postgres import get_face_database
from database import redis_client, RedisCache

class GeminiMemoryManager:
    """
    Управление памятью пользователя для Gemini Live API с использованием PostgreSQL
    """

    def __init__(self):
        self.memory_cache: Dict[str, Dict] = {}  # Локальный кэш
        self.max_cache_size = 100
        self.cache_helper = RedisCache(redis_client)

    async def get_user_context(self, user_id: str, user_name: str) -> str:
        """
        Получить контекст пользователя для Gemini system_instruction
        """
        try:
            db = await get_face_database()
            
            # 1. Получить историю и профиль из БД
            history = await db.get_user_history(user_id)
            
            if not history:
                logger.info(f"🆕 Новый пользователь: {user_name}")
                return self._build_system_prompt(user_name, {}, [])

            # 2. Построить контекст на основе реальных данных из Postgres
            user_data = history.get("profile_data", {})
            # Добавим статистику в user_data
            user_data["average_emotion"] = history.get("average_emotion")
            user_data["interaction_count"] = history.get("interaction_count")
            
            # 3. Получить недавние события из истории сообщений
            recent_events = []
            for msg in history.get("conversation_history", []):
                speaker = msg.get("speaker", "user")
                text = msg.get("message", "")
                recent_events.append({"summary": f"{speaker}: {text}"})

            return self._build_system_prompt(user_name, user_data, recent_events)

        except Exception as e:
            logger.error(f"❌ Ошибка при получении контекста: {e}")
            return f"Ты - дружелюбный осьминог. Твоего собеседника зовут {user_name}."

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Записать взаимодействие в PostgreSQL
        """
        try:
            db = await get_face_database()
            
            emotion = data.get("emotion") if interaction_type == "emotion" else None
            action = data.get("action") if interaction_type == "action" else None
            message = data.get("text") if interaction_type == "message" else None
            speaker = data.get("speaker", "user")

            await db.add_interaction(
                user_id=user_id,
                emotion=emotion,
                action=action,
                message=message,
                speaker=speaker
            )
            
            logger.debug(f"📝 Взаимодействие ({interaction_type}) записано в Postgres для {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при записи взаимодействия: {e}")
            return False

    async def recall_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Поиск по истории (пока простой поиск по сообщениям)
        """
        db = await get_face_database()
        history = await db.get_user_history(user_id)
        if not history:
            return []
        
        # Пока просто возвращаем последние сообщения как "воспоминания"
        return history.get("conversation_history", [])[-limit:]

    def _build_system_prompt(
        self,
        user_name: str,
        user_data: Dict,
        recent_events: List[Dict]
    ) -> str:
        """
        Построить system_instruction для Gemini
        """
        prompt = f"""Ты - веселый, дружелюбный и немного ироничный глубоководный осьминог.
Ты общаешься с пользователем по имени {user_name}.

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
"""
        if user_data:
            if user_data.get("preferences"):
                prompt += f"- Предпочтения: {user_data['preferences']}\n"
            if user_data.get("interaction_count"):
                prompt += f"- Вы общались уже {user_data['interaction_count']} раз\n"
            if user_data.get("average_emotion"):
                prompt += f"- Чаще всего он в настроении: {user_data['average_emotion']}\n"

        if recent_events:
            prompt += "\nПОСЛЕДНИЕ СОБЫТИЯ В ВАШЕМ ДИАЛОГЕ:\n"
            for event in recent_events[-3:]:
                prompt += f"- {event.get('summary')}\n"

        prompt += """
ТВОИ ПРАВИЛА:
1. Отвечай кратко (1-2 предложения).
2. Используй морские метафоры, но не переборщи.
3. Реагируй на эмоции собеседника.
4. Если ты его уже знаешь, поприветствуй как старого друга.

Давай начнем общение!"""
        return prompt

# Глобальный экземпляр
_memory_manager: Optional[GeminiMemoryManager] = None

async def get_memory_manager() -> GeminiMemoryManager:
    """Получить глобальный менеджер памяти"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = GeminiMemoryManager()
    return _memory_manager
