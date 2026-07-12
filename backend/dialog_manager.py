"""
Dialog Manager - управляет диалогом с пользователем через Gemini
Обрабатывает регистрацию новых пользователей и сохраняет разговоры в БД
"""

import asyncio
import json
import time
import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime

from face_db_postgres import get_face_database

logger = logging.getLogger(__name__)


class DialogManager:
    """
    Управляет диалогом с пользователем:
    1. Обнаруживает неизвестного пользователя
    2. Запрашивает имя через голос
    3. Инициирует photobooth для регистрации
    4. Сохраняет разговор в БД
    5. При следующей встрече подтягивает контекст
    """

    def __init__(self):
        self.db = None
        self.current_user_id: Optional[str] = None
        self.current_user_name: Optional[str] = None
        self.conversation_buffer: List[Dict] = []
        self.is_registering = False
        self.registration_start_time: Optional[float] = None
        self.registration_timeout_seconds = 30  # 30 seconds timeout

        # Callbacks
        self.on_name_requested: Optional[Callable] = None  # Когда просим имя
        self.on_registration_start: Optional[Callable] = None  # Начало photobooth
        self.on_registration_complete: Optional[Callable] = None  # Конец photobooth
        self.on_user_recognized: Optional[Callable] = None  # Узнали пользователя

    async def init(self):
        """Инициализировать менеджер"""
        self.db = await get_face_database()
        logger.info("✅ Dialog Manager инициализирован")

    def _check_registration_timeout(self) -> bool:
        """
        Проверить истек ли timeout регистрации
        Returns: True если timeout истек, False иначе
        """
        if not self.is_registering or not self.registration_start_time:
            return False

        elapsed = time.time() - self.registration_start_time
        if elapsed > self.registration_timeout_seconds:
            logger.warning(f"⏱️⏱️⏱️ TIMEOUT РЕГИСТРАЦИИ: {elapsed:.1f}s > {self.registration_timeout_seconds}s, СБРОС is_registering=False ⏱️⏱️⏱️")
            self.is_registering = False
            self.registration_start_time = None
            self.conversation_buffer = []
            return True

        return False

    async def on_face_unknown(self) -> Dict:
        """
        Лицо не узнано - запустить процесс регистрации

        Returns:
            {status, message, action}
        """
        # Проверить timeout регистрации
        self._check_registration_timeout()

        if self.is_registering:
            logger.warning("⚠️ Уже в процессе регистрации")
            return {"status": "error", "message": "Already registering"}

        self.is_registering = True
        self.registration_start_time = time.time()
        self.conversation_buffer = []

        logger.info(f"🆕 Начало регистрации нового пользователя (is_registering={self.is_registering})")

        # Callback: просим имя
        if self.on_name_requested:
            await self.on_name_requested()

        return {
            "status": "ask_name",
            "message": "Привет! Мы не знакомы. Спроси, как меня зовут, и давай знакомиться! 🐙",
            "action": "ask_name"
        }

    async def process_user_speech(self, text: str) -> Dict:
        """
        Обработка речи пользователя в контексте регистрации
        """
        logger.info(f"🎤 DialogManager.process_user_speech: text='{text}', is_registering={self.is_registering}, current_user={self.current_user_id}")

        if not self.is_registering:
            logger.warning(f"⚠️ Не в режиме регистрации (current_user={self.current_user_id})")
            return {"status": "error", "message": "Not in registration mode"}

        # Пропустить если это системное приглашение (которое мы инжектим)
        if "Спроси, как меня зовут" in text or "Мы не знакомы" in text:
            logger.info("ℹ️ Skipping system greeting message")
            return {"status": "waiting", "message": "Waiting for user to ask name"}

        # Сохранить в буфер разговора
        self.conversation_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "speaker": "user",
            "text": text
        })

        # Попробовать извлечь имя
        user_name = self._extract_name(text)
        logger.info(f"🔍 Name extraction result: '{user_name}'")
        
        if not user_name:
            msg = "Я не совсем расслышал твоё имя. Повтори, пожалуйста, как тебя зовут?"
            logger.warning(f"⚠️ Не удалось парсить имя из: {text}")
            self.conversation_buffer.append({"speaker": "avatar", "text": msg})
            return {
                "status": "retry",
                "message": "Не расслышал. Повтори пожалуйста.",
                "action": "ask_name_again"
            }

        self.current_user_name = user_name
        logger.info(f"📝 Имя пользователя: {user_name}")

        # Callback: начинаем photobooth
        if self.on_registration_start:
            await self.on_registration_start(user_name)

        return {
            "status": "start_photobooth",
            "user_name": user_name,
            "action": "photobooth_start",
            "message": f"Спасибо, {user_name}! Сейчас сделаю несколько фото для запоминания."
        }

    async def register_user_with_embedding(
        self,
        user_name: str,
        embedding: List[float]
    ) -> Dict:
        """
        Зарегистрировать пользователя с его embedding

        Args:
            user_name: Имя пользователя
            embedding: Усредненный embedding из photobooth

        Returns:
            {user_id, status}
        """
        try:
            # Регистрировать в БД
            result = await self.db.register_new_user(
                name=user_name,
                embedding=embedding,
                profile_data={
                    "registration_timestamp": time.time(),
                    "registration_method": "dialog_photobooth"
                }
            )

            self.current_user_id = result["user_id"]
            self.current_user_name = user_name

            # Сохранить начальный разговор
            await self._save_conversation_to_db(
                user_id=result["user_id"],
                user_name=user_name
            )

            logger.info(f"✅ Пользователь зарегистрирован: {user_name} (ID: {result['user_id']})")

            self.is_registering = False
            self.registration_start_time = None
            self.conversation_buffer = []

            # Callback: регистрация завершена
            if self.on_registration_complete:
                await self.on_registration_complete(user_name)

            return {
                "status": "registered",
                "user_id": result["user_id"],
                "user_name": user_name,
                "message": f"Отлично, {user_name}! Я запомнил твое лицо! 🐙✨"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка регистрации: {e}")
            self.is_registering = False
            self.registration_start_time = None
            return {"status": "error", "message": str(e)}

    async def on_user_recognized(self, user_id: str, user_name: str, confidence: float) -> Dict:
        """
        Пользователь узнан - загрузить контекст

        Args:
            user_id: ID пользователя
            user_name: Имя пользователя
            confidence: Уверенность распознавания

        Returns:
            {user_data, conversation_context}
        """
        self.current_user_id = user_id
        self.current_user_name = user_name
        # Если нашли известного пользователя, сбрасываем регистрацию
        self.is_registering = False
        self.registration_start_time = None

        try:
            # Загрузить данные пользователя для контекста
            user_data = await self.db.get_user_history(user_id)

            if not user_data:
                logger.warning(f"⚠️ Данные пользователя не найдены: {user_id}")
                return {
                    "user_id": user_id,
                    "user_name": user_name,
                    "message": f"Привет, {user_name}! Рад тебя видеть!"
                }

            # Подготовить контекст для Gemini
            context = self._prepare_gemini_context(user_data)

            logger.info(f"✅ Контекст загружен для: {user_name}")

            if self.on_user_recognized:
                await self.on_user_recognized(user_data)

            return {
                "user_id": user_id,
                "user_name": user_name,
                "confidence": confidence,
                "context": context,
                "message": f"Привет, {user_name}! Как дела? 👋",
                "last_interaction": user_data.get("last_seen"),
                "interaction_count": user_data.get("interaction_count")
            }

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки контекста: {e}")
            return {
                "user_id": user_id,
                "user_name": user_name,
                "message": f"Привет, {user_name}!"
            }

    async def log_avatar_speech(self, text: str) -> bool:
        """
        Записать что сказал аватар

        Args:
            text: Текст аватара

        Returns:
            True если успешно
        """
        try:
            self.conversation_buffer.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": "avatar",
                "text": text
            })

            # Если пользователь узнан, сохранить в БД в реальном времени
            if self.current_user_id:
                await self.db.add_interaction(
                    user_id=self.current_user_id,
                    message=text,
                    speaker="avatar"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка логирования: {e}")
            return False

    async def log_emotion_and_action(
        self,
        emotion: str,
        action: Optional[str] = None
    ) -> bool:
        """
        Записать эмоцию и действие аватара

        Args:
            emotion: Эмоция (happy, sad, etc)
            action: Действие (greet, curious, etc)

        Returns:
            True если успешно
        """
        try:
            if self.current_user_id:
                await self.db.add_interaction(
                    user_id=self.current_user_id,
                    emotion=emotion,
                    action=action
                )
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка логирования эмоции: {e}")
            return False

    def _extract_name(self, text: str) -> Optional[str]:
        """
        Парсить имя из текста пользователя
        """
        logger.info(f"🔍 Analyzing text for name: '{text}'")
        text_clean = text.strip()
        text_lower = text_clean.lower()

        # 1. Пробуем строгие паттерны - более специфичные ПЕРВЫМИ!
        patterns = [
            "меня зовут ",  # "Меня зовут Миша" -> берем "Миша"
            "мое имя ",     # "Мое имя Иван" -> берем "Иван"
            "я ",           # "Я Петр" -> берем "Петр"
            "зовут ",       # "Зовут меня Дмитрий" -> берем "меня" (СТОП-слово!)
            "имя ",         # "Имя мое Сергей" -> берем "мое" (СТОП-слово!)
        ]

        # Стоп-слова (служебные слова, которые точно не имена)
        stopwords = {
            "меня", "тебя", "вас", "ему", "ей", "им",
            "как", "что", "кто", "где", "когда", "зачем", "почему",
            "октопус", "привет", "здравствуй", "это", "есть", "быть",
            "зовут", "имя", "мое", "твое", "его", "ее"
        }

        for pattern in patterns:
            idx = text_lower.find(pattern)
            if idx != -1:
                # Взять часть после паттерна
                after_pattern = text_clean[idx + len(pattern):].strip()
                words = after_pattern.split()
                if words:
                    # Чистим от знаков препинания
                    raw_name = words[0].rstrip('.,!?;:')
                    if not raw_name: continue

                    name = raw_name.capitalize()

                    # Фильтры
                    if name.lower() in stopwords:
                        logger.info(f"⚠️ Rejected candidate '{name}' (stopword)")
                        continue

                    if len(name) < 2:
                        logger.info(f"⚠️ Rejected candidate '{name}' (too short)")
                        continue

                    logger.info(f"✅ Extracted name '{name}' via pattern '{pattern}'")
                    return name

        # 2. Если паттерны не сработали - ищем просто слова с большой буквы
        # Или если предложение короткое (1-2 слова) - считаем это именем
        words = text_clean.split()
        
        # Если всего одно слово - скорее всего это имя
        if len(words) == 1:
            name = words[0].rstrip('.,!?').capitalize()
            if len(name) > 1 and name.lower() not in ["привет", "да", "нет", "ок", "хорошо", "слушай"]:
                 logger.info(f"✅ Extracted single-word name '{name}'")
                 return name

        # Ищем слово с заглавной буквы, которое не в начале предложения (или в начале, если это не служебное слово)
        for i, word in enumerate(words):
            clean_word = word.rstrip('.,!?')
            if not clean_word: continue
            
            # Если слово с заглавной
            if clean_word[0].isupper() and len(clean_word) > 1:
                candidate = clean_word.capitalize()
                
                # Список слов которые могут быть с заглавной но не имена (начало предложения)
                # Если это ПЕРВОЕ слово, то критерии строже (должно быть не в словаре обычных слов)
                if i == 0:
                    common_starters = ["Привет", "Здравствуй", "Слушай", "Скажи", "Меня", "Мое", "Я", "Как", "Что"]
                    if candidate in common_starters:
                        continue
                
                # Фильтр стоп-слов
                if candidate.lower() in ["октопус", "тебя", "меня"]:
                    continue

                logger.info(f"✅ Extracted capitalized candidate '{candidate}'")
                return candidate

        logger.info("❌ Name extraction failed")
        return None

    def _prepare_gemini_context(self, user_data: Dict) -> str:
        """
        Подготовить контекст для Gemini system instruction

        Args:
            user_data: Данные пользователя из БД

        Returns:
            Текст контекста
        """
        name = user_data.get("name", "Friend")
        interaction_count = user_data.get("interaction_count", 0)
        avg_emotion = user_data.get("average_emotion", "neutral")
        last_seen = user_data.get("last_seen")

        # Последние разговоры
        conversation_history = user_data.get("conversation_history", [])
        recent_talks = conversation_history[-3:] if conversation_history else []

        context = f"""
Пользователь {name}:
- Встречи: {interaction_count}
- Любимая эмоция: {avg_emotion}
- Был(а): {last_seen}

Недавние разговоры:
"""
        for msg in recent_talks:
            speaker = msg.get("timestamp", "")
            text = msg.get("message", "")[:100]
            context += f"\n{text}"

        return context

    async def _save_conversation_to_db(
        self,
        user_id: str,
        user_name: str
    ) -> bool:
        """
        Сохранить весь буфер разговора в БД

        Args:
            user_id: ID пользователя
            user_name: Имя пользователя

        Returns:
            True если успешно
        """
        try:
            for msg in self.conversation_buffer:
                text = msg.get("text", "")
                await self.db.add_interaction(
                    user_id=user_id,
                    message=text
                )

            logger.info(f"✅ Разговор сохранен для {user_name} ({len(self.conversation_buffer)} сообщений)")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения разговора: {e}")
            return False

    def get_current_user(self) -> Optional[Dict]:
        """Получить текущего пользователя"""
        if self.current_user_id:
            return {
                "user_id": self.current_user_id,
                "user_name": self.current_user_name,
                "is_registering": self.is_registering
            }
        return None

    def reset(self):
        """Сбросить состояние"""
        self.current_user_id = None
        self.current_user_name = None
        self.conversation_buffer = []
        self.is_registering = False
        self.registration_start_time = None
        logger.info("🔄 Dialog Manager сброшен")


# Глобальный экземпляр
_dialog_manager: Optional[DialogManager] = None


async def get_dialog_manager() -> DialogManager:
    """Получить глобальный экземпляр Dialog Manager"""
    global _dialog_manager
    if _dialog_manager is None:
        _dialog_manager = DialogManager()
        await _dialog_manager.init()
    return _dialog_manager
