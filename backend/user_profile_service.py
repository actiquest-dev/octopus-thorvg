"""
User Profile Service
Загрузка полного профиля пользователя с историей разговоров и ключевыми воспоминаниями
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from loguru import logger
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from models import User, FaceProfile, ConversationHistory, UserAction
from face_user_repository import FaceUserRepository


class UserProfileService:
    """Сервис для загрузки полного профиля пользователя с историей"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repo = FaceUserRepository(db_session)

    async def load_full_profile(
        self,
        user_id: str,
        include_history: bool = True,
        history_limit: int = 10,
        include_actions: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Загрузить полный профиль пользователя со всей историей

        Args:
            user_id: ID пользователя
            include_history: Загружать ли историю разговоров
            history_limit: Количество сообщений из истории
            include_actions: Загружать ли логирование действий

        Returns:
            Полный профиль с историей или None
        """
        try:
            logger.info(f"📋 Загружаю полный профиль для {user_id}")

            # Получить пользователя
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"❌ Пользователь не найден: {user_id}")
                return None

            profile = {
                "user": user.to_dict(),
                "face_profiles": [],
                "conversation_history": [],
                "user_actions": [],
                "summary": {},
                "last_interaction": None,
                "total_interactions": user.interaction_count
            }

            # === Получить все лица пользователя ===
            try:
                face_profiles = await self.repo.get_face_profiles(user_id)
                profile["face_profiles"] = [fp.to_dict() for fp in face_profiles]
                logger.info(f"📸 Найдено {len(face_profiles)} лиц для {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки лиц: {e}")

            # === Получить историю разговоров ===
            if include_history:
                try:
                    result = await self.db.execute(
                        select(ConversationHistory)
                        .where(ConversationHistory.user_id == user_id)
                        .order_by(desc(ConversationHistory.created_at))
                        .limit(history_limit)
                    )
                    conversations = result.scalars().all()
                    profile["conversation_history"] = [
                        c.to_dict() for c in reversed(conversations)  # Обратный порядок (старые→новые)
                    ]
                    logger.info(f"💬 Загружено {len(conversations)} сообщений из истории")

                    # Получить последнее взаимодействие
                    if conversations:
                        profile["last_interaction"] = conversations[0].created_at.isoformat()

                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки истории: {e}")

            # === Получить логирование действий ===
            if include_actions:
                try:
                    result = await self.db.execute(
                        select(UserAction)
                        .where(UserAction.user_id == user_id)
                        .order_by(desc(UserAction.created_at))
                        .limit(5)
                    )
                    actions = result.scalars().all()
                    profile["user_actions"] = [a.to_dict() for a in reversed(actions)]
                    logger.info(f"📊 Загружено {len(actions)} действий")
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки действий: {e}")

            # === Сгенерировать резюме ===
            try:
                summary = await self._generate_profile_summary(user, profile)
                profile["summary"] = summary
            except Exception as e:
                logger.error(f"❌ Ошибка генерации резюме: {e}")

            logger.info(f"✅ Полный профиль загружен для {user_id}")
            return profile

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профиля: {e}")
            return None

    async def _generate_profile_summary(
        self,
        user: User,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сгенерировать резюме профиля для аватара

        Args:
            user: Объект пользователя
            profile: Профиль с историей

        Returns:
            Резюме: основные факты, эмоции, интересы
        """
        summary = {
            "name": user.name,
            "interaction_count": user.interaction_count,
            "member_since": user.created_at.isoformat() if user.created_at else None,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None,
            "key_facts": [],
            "emotions": {},
            "interests": [],
            "conversation_topics": [],
            "personality_traits": [],
        }

        # === Анализировать историю ===
        conversations = profile.get("conversation_history", [])

        if conversations:
            # Подсчитать эмоции
            emotions = {}
            for conv in conversations:
                emotion = conv.get("emotion")
                if emotion:
                    emotions[emotion] = emotions.get(emotion, 0) + 1

            # Найти доминирующую эмоцию
            if emotions:
                dominant_emotion = max(emotions, key=emotions.get)
                summary["emotions"] = emotions
                summary["primary_emotion"] = dominant_emotion

            # Извлечь темы разговоров
            topics = set()
            for conv in conversations:
                tags = conv.get("context_tags", [])
                if tags:
                    topics.update(tags)
            summary["conversation_topics"] = list(topics)

            # Подсчитать частоту слов (минимальный анализ)
            all_content = " ".join([c.get("content", "") for c in conversations])
            summary["word_count"] = len(all_content.split())

        # === Добавить информацию из профиля ===
        if user.profile_data:
            summary["profile_data"] = user.profile_data

        # === Персональные черты на основе взаимодействий ===
        interaction_count = user.interaction_count
        if interaction_count > 100:
            summary["personality_traits"].append("very_engaged")
        elif interaction_count > 50:
            summary["personality_traits"].append("engaged")
        elif interaction_count > 10:
            summary["personality_traits"].append("regular_user")
        else:
            summary["personality_traits"].append("new_user")

        return summary

    async def extract_key_memories(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Извлечь ключевые воспоминания из истории для аватара

        Args:
            user_id: ID пользователя
            limit: Количество воспоминаний

        Returns:
            Список ключевых моментов
        """
        try:
            logger.info(f"🧠 Извлекаю ключевые воспоминания для {user_id}")

            result = await self.db.execute(
                select(ConversationHistory)
                .where(ConversationHistory.user_id == user_id)
                .where(ConversationHistory.role == "user")  # Только сообщения пользователя
                .order_by(desc(ConversationHistory.created_at))
                .limit(limit * 3)  # Получить больше, потом отфильтровать
            )
            conversations = result.scalars().all()

            # Фильтровать по длине и важности
            memories = []
            for conv in conversations:
                content = conv.content
                # Выбирать сообщения от 20 до 500 символов (не слишком короткие, не слишком длинные)
                if 20 < len(content) < 500 and conv.emotion != "neutral":
                    memories.append({
                        "text": content,
                        "emotion": conv.emotion,
                        "date": conv.created_at.isoformat(),
                        "timestamp": conv.created_at.timestamp()
                    })

                if len(memories) >= limit:
                    break

            logger.info(f"✅ Извлечено {len(memories)} ключевых воспоминаний")
            return memories

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения воспоминаний: {e}")
            return []

    async def get_context_for_greeting(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Получить контекст для персонализированного приветствия аватара

        Args:
            user_id: ID пользователя

        Returns:
            Контекст для генерации приветствия
        """
        try:
            logger.info(f"👋 Подготавливаю контекст для приветствия {user_id}")

            user = await self.repo.get_user_by_id(user_id)
            if not user:
                return None

            context = {
                "user_name": user.name,
                "times_met": user.interaction_count,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                "days_since_last_visit": None,
                "memory_snippets": [],
                "emotional_state": "neutral",
                "conversation_style": "friendly"
            }

            # === Рассчитать дни с последнего визита ===
            if user.last_seen:
                days_ago = (datetime.utcnow() - user.last_seen).days
                context["days_since_last_visit"] = days_ago

                # Выбрать приветствие на основе времени
                if days_ago == 0:
                    context["greeting_type"] = "welcome_back_today"
                elif days_ago == 1:
                    context["greeting_type"] = "welcome_back_yesterday"
                elif days_ago < 7:
                    context["greeting_type"] = "welcome_back_week"
                elif days_ago < 30:
                    context["greeting_type"] = "welcome_back_month"
                else:
                    context["greeting_type"] = "welcome_back_long_time"
            else:
                context["greeting_type"] = "first_time"

            # === Получить ключевые воспоминания ===
            memories = await self.extract_key_memories(user_id, limit=3)
            if memories:
                context["memory_snippets"] = [m["text"][:100] + "..." for m in memories]

            # === Определить эмоциональное состояние ===
            result = await self.db.execute(
                select(ConversationHistory.emotion, func.count(ConversationHistory.id))
                .where(ConversationHistory.user_id == user_id)
                .group_by(ConversationHistory.emotion)
                .order_by(desc(func.count(ConversationHistory.id)))
                .limit(1)
            )
            emotion_row = result.first()
            if emotion_row:
                context["emotional_state"] = emotion_row[0] or "neutral"

            logger.info(f"✅ Контекст приветствия подготовлен")
            return context

        except Exception as e:
            logger.error(f"❌ Ошибка подготовки контекста: {e}")
            return None

    async def save_conversation_turn(
        self,
        user_id: str,
        role: str,
        content: str,
        emotion: Optional[str] = None,
        context_tags: Optional[List[str]] = None
    ) -> Optional[ConversationHistory]:
        """
        Сохранить одно сообщение в историю разговора

        Args:
            user_id: ID пользователя
            role: "user" или "assistant"
            content: Текст сообщения
            emotion: Определённая эмоция
            context_tags: Теги контекста

        Returns:
            Сохранённое сообщение
        """
        try:
            conversation = ConversationHistory(
                user_id=user_id,
                role=role,
                content=content,
                emotion=emotion,
                context_tags=context_tags or []
            )
            self.db.add(conversation)
            await self.db.flush()
            logger.info(f"💬 Сообщение сохранено для {user_id}")
            return conversation
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
            return None

    async def get_conversation_context(
        self,
        user_id: str,
        max_messages: int = 20
    ) -> str:
        """
        Получить контекст всей последней переписки для Gemini

        Args:
            user_id: ID пользователя
            max_messages: Максимум сообщений

        Returns:
            Форматированный контекст для LLM
        """
        try:
            result = await self.db.execute(
                select(ConversationHistory)
                .where(ConversationHistory.user_id == user_id)
                .order_by(desc(ConversationHistory.created_at))
                .limit(max_messages)
            )
            conversations = result.scalars().all()

            # Обратный порядок (старые→новые)
            conversations = list(reversed(conversations))

            # Форматировать
            context_lines = []
            for conv in conversations:
                role_prefix = "User" if conv.role == "user" else "Avatar"
                timestamp = conv.created_at.strftime("%H:%M") if conv.created_at else ""

                line = f"[{timestamp}] {role_prefix}: {conv.content}"
                if conv.emotion:
                    line += f" (emotion: {conv.emotion})"

                context_lines.append(line)

            context = "\n".join(context_lines)
            logger.info(f"📚 Контекст с {len(conversations)} сообщений подготовлен")
            return context

        except Exception as e:
            logger.error(f"❌ Ошибка получения контекста: {e}")
            return ""

    async def get_user_summary_for_llm(self, user_id: str) -> str:
        """
        Получить резюме пользователя для промпта LLM

        Args:
            user_id: ID пользователя

        Returns:
            Резюме в текстовом формате
        """
        try:
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                return ""

            lines = [
                f"=== Информация о пользователе ===",
                f"Имя: {user.name}",
                f"Встречи: {user.interaction_count}",
                f"Первый раз: {user.created_at.strftime('%Y-%m-%d') if user.created_at else 'неизвестно'}",
            ]

            if user.phone:
                lines.append(f"Телефон: {user.phone}")

            if user.profile_data:
                if isinstance(user.profile_data, dict):
                    for key, value in user.profile_data.items():
                        lines.append(f"{key}: {value}")

            summary = "\n".join(lines)
            return summary

        except Exception as e:
            logger.error(f"❌ Ошибка генерации резюме: {e}")
            return ""
