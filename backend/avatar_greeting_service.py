"""
Avatar Greeting Service
Генерация персонализированных приветствий аватара на основе истории пользователя
"""

from typing import Optional, Dict, Any
from loguru import logger
import google.generativeai as genai

from gemini_integration import GeminiService
from user_profile_service import UserProfileService
from sqlalchemy.ext.asyncio import AsyncSession


class AvatarGreetingService:
    """Сервис для генерации приветствий аватара"""

    def __init__(self, db_session: AsyncSession, gemini_service: Optional[GeminiService] = None):
        self.db = db_session
        self.profile_service = UserProfileService(db_session)
        self.gemini_service = gemini_service or GeminiService()

    async def generate_greeting(
        self,
        user_id: str,
        confidence: float = 0.95
    ) -> Dict[str, Any]:
        """
        Сгенерировать персонализированное приветствие

        Args:
            user_id: ID пользователя
            confidence: Уверенность в идентификации (0-1)

        Returns:
            {greeting_text, tone, memories, suggestions}
        """
        try:
            logger.info(f"👋 Генерирую приветствие для {user_id} (confidence: {confidence:.2f})")

            # === Получить контекст ===
            context = await self.profile_service.get_context_for_greeting(user_id)
            if not context:
                return self._generic_greeting()

            # === Загрузить полный профиль ===
            profile = await self.profile_service.load_full_profile(
                user_id,
                include_history=True,
                history_limit=5
            )

            # === Подготовить информацию для промпта ===
            user_summary = await self.profile_service.get_user_summary_for_llm(user_id)
            conversation_context = await self.profile_service.get_conversation_context(
                user_id,
                max_messages=5
            )
            key_memories = await self.profile_service.extract_key_memories(user_id, limit=3)

            # === Построить промпт ===
            prompt = self._build_greeting_prompt(
                user_id=user_id,
                context=context,
                user_summary=user_summary,
                conversation_context=conversation_context,
                key_memories=key_memories,
                confidence=confidence
            )

            # === Сгенерировать ответ от Gemini ===
            greeting_text = await self.gemini_service.generate_response(
                query=prompt,
                user_name=context.get("user_name", "Friend"),
                user_context=user_summary,
                user_profile=profile.get("summary", {}) if profile else {}
            )

            result = {
                "greeting": greeting_text,
                "user_name": context.get("user_name"),
                "times_met": context.get("times_met", 0),
                "greeting_type": context.get("greeting_type"),
                "tone": self._determine_tone(context),
                "memories": key_memories[:2],  # Вернуть 2 ключевых воспоминания
                "suggestions": await self._generate_suggestions(user_id, context),
                "confidence": confidence,
                "emotional_state": context.get("emotional_state", "neutral")
            }

            logger.info(f"✅ Приветствие сгенерировано для {user_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка генерации приветствия: {e}")
            return self._generic_greeting()

    def _build_greeting_prompt(
        self,
        user_id: str,
        context: Dict[str, Any],
        user_summary: str,
        conversation_context: str,
        key_memories: list,
        confidence: float
    ) -> str:
        """Построить промпт для Gemini"""

        greeting_instructions = {
            "first_time": "Это первое встреча с пользователем. Будь теплым и приветливым, представься.",
            "welcome_back_today": "Пользователь был здесь сегодня. Помни о его предыдущих визитах.",
            "welcome_back_yesterday": "Пользователь был здесь вчера. Упомяни это в приветствии.",
            "welcome_back_week": "Пользователь не был здесь неделю. Рады видеть его снова!",
            "welcome_back_month": "Давно не виделись! Пользователь месяц не был здесь.",
            "welcome_back_long_time": "Очень давно! Пользователь был здесь давно. Горячее приветствие!"
        }

        greeting_type = context.get("greeting_type", "welcome_back_today")
        instruction = greeting_instructions.get(greeting_type, "Приветствуй пользователя!")

        memories_text = ""
        if key_memories:
            memories_text = "\n\nОсновные воспоминания о пользователе:\n"
            for i, mem in enumerate(key_memories, 1):
                memories_text += f"- {mem['text'][:80]}... (эмоция: {mem['emotion']})\n"

        times_met = context.get("times_met", 0)
        times_info = f"Вы встречались {times_met} раз" if times_met > 1 else "Это ваша первая встреча"

        prompt = f"""Ты дружелюбный виртуальный аватар.

{instruction}

{times_info}

{user_summary}

{memories_text}

ПОСЛЕДНЯЯ ПЕРЕПИСКА:
{conversation_context if conversation_context else "(первый разговор)"}

Генерируй краткое, теплое приветствие (1-2 предложения) которое:
1. Обращается к пользователю по имени
2. Показывает что ты помнишь о нём/ней
3. Отражает его/её эмоциональное состояние
4. Проявляет искренний интерес

Ответ только приветствие, без объяснений."""

        return prompt

    def _determine_tone(self, context: Dict[str, Any]) -> str:
        """Определить тон приветствия"""
        emotional_state = context.get("emotional_state", "neutral")
        greeting_type = context.get("greeting_type", "welcome_back_today")

        # Выбрать тон на основе эмоции и типа приветствия
        if emotional_state in ["happy", "excited"]:
            return "enthusiastic"
        elif emotional_state in ["sad", "angry"]:
            return "compassionate"
        elif greeting_type == "first_time":
            return "warm"
        elif "long_time" in greeting_type:
            return "joyful"
        else:
            return "friendly"

    async def _generate_suggestions(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> list:
        """
        Сгенерировать предложения для продолжения разговора

        Args:
            user_id: ID пользователя
            context: Контекст приветствия

        Returns:
            Список предложений
        """
        try:
            # Получить темы разговоров
            profile = await self.profile_service.load_full_profile(
                user_id,
                include_history=False
            )

            if not profile:
                return ["Как дела?", "Чем я могу помочь?", "Что-нибудь интересного?"]

            summary = profile.get("summary", {})
            topics = summary.get("conversation_topics", [])

            suggestions = []

            # Добавить предложения на основе интересов
            if topics:
                for topic in topics[:2]:
                    suggestions.append(f"Расскажи ещё о {topic}")

            # Добавить общие предложения
            suggestions.extend([
                "Как прошёл твой день?",
                "Есть ли что-нибудь новое?",
                "Чем я могу помочь?"
            ])

            return suggestions[:3]  # Вернуть 3 предложения

        except Exception as e:
            logger.error(f"❌ Ошибка генерации предложений: {e}")
            return ["Как дела?", "Чем я могу помочь?"]

    def _generic_greeting(self) -> Dict[str, Any]:
        """Стандартное приветствие если что-то пошло не так"""
        return {
            "greeting": "Привет! Рада тебя видеть! 👋",
            "user_name": "Friend",
            "times_met": 0,
            "tone": "friendly",
            "memories": [],
            "suggestions": ["Как дела?", "Чем я могу помочь?", "Расскажи мне о себе"],
            "confidence": 0.0,
            "emotional_state": "neutral"
        }

    async def get_memory_recall(
        self,
        user_id: str,
        max_memories: int = 5
    ) -> Dict[str, Any]:
        """
        Получить вспоминаемые моменты из истории

        Args:
            user_id: ID пользователя
            max_memories: Максимум воспоминаний

        Returns:
            {memories, summary, key_topics}
        """
        try:
            logger.info(f"🧠 Вызываю воспоминания для {user_id}")

            memories = await self.profile_service.extract_key_memories(user_id, limit=max_memories)

            profile = await self.profile_service.load_full_profile(user_id, include_history=False)
            summary = profile.get("summary", {}) if profile else {}

            recall = {
                "memories": memories,
                "key_facts": summary.get("key_facts", []),
                "topics": summary.get("conversation_topics", []),
                "personality": summary.get("personality_traits", []),
                "primary_emotion": summary.get("primary_emotion", "neutral"),
                "total_interactions": summary.get("interaction_count", 0)
            }

            logger.info(f"✅ Воспоминания вызваны: {len(memories)} моментов")
            return recall

        except Exception as e:
            logger.error(f"❌ Ошибка вызова воспоминаний: {e}")
            return {"memories": [], "error": str(e)}

    async def remember_conversation(
        self,
        user_id: str,
        user_message: str,
        avatar_response: str,
        emotion: Optional[str] = None
    ) -> bool:
        """
        Запомнить разговор в историю

        Args:
            user_id: ID пользователя
            user_message: Сообщение пользователя
            avatar_response: Ответ аватара
            emotion: Определённая эмоция

        Returns:
            Успешность сохранения
        """
        try:
            # Сохранить сообщение пользователя
            await self.profile_service.save_conversation_turn(
                user_id=user_id,
                role="user",
                content=user_message,
                emotion=emotion
            )

            # Сохранить ответ аватара
            await self.profile_service.save_conversation_turn(
                user_id=user_id,
                role="assistant",
                content=avatar_response,
                emotion=None
            )

            await self.db.commit()
            logger.info(f"💾 Разговор сохранён для {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения разговора: {e}")
            await self.db.rollback()
            return False
