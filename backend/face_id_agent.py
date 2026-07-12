"""
Face ID Registration Agent
Локальный Gemini агент для диалога о регистрации нового пользователя
Работает асинхронно, не блокируя видео-стрим
"""

import asyncio
import logging
from typing import Optional, Callable
from google import genai
from google.genai import types
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


class FaceIDRegistrationAgent:
    """
    Агент для диалога регистрации новых пользователей

    Workflow:
    1. Пользователь смотрит в камеру
    2. Лицо не найдено в БД
    3. Аватар: "Привет! Я тебя не знаю. Давай я внесу тебя в базу! Как тебя зовут?"
    4. Пользователь: "Меня зовут Иван"
    5. Аватар: "Спасибо, Иван! Сейчас я сделаю несколько фото для запоминания. Посмотри прямо на камеру и улыбнись!"
    6. Запускается PHOTOBOOTH action
    7. Берутся 3-5 кадров, усредняются embeddings
    8. Пользователь зарегистрирован ✅
    9. Аватар: "Отлично! Теперь я тебя помню, Иван!"
    """

    def __init__(self):
        self.client = None
        self.session = None
        self.is_running = False
        self.registered_callback: Optional[Callable] = None

    async def init(self):
        """Инициализировать Gemini сессию для агента"""
        self.client = genai.Client(vertexai=True, project="upheld-rain-484209-a6", location="global")

        self.session = await self.client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=types.LiveConnectConfig(
                response_modalities=["text"],  # Только текст, без аудио (экономим ресурсы)
                enable_affective_dialog=True,
                system_instruction="""Ты - веселый дружелюбный осьминог.
Помогаешь новым пользователям зарегистрироваться в базе лиц.

Инструкции:
1. Представься коротко и дружелюбно
2. Попроси имя пользователя
3. После получения имени, дай инструкцию смотреть в камеру и улыбаться
4. Произнеси магическое слово "PHOTOBOOTH_START" для начала регистрации фото
5. После завершения скажи "PHOTOBOOTH_DONE"
6. Пожелай успехов!

Разговаривай на русском языке. Будь позитивным и веселым!
Ответы должны быть короткими (1-2 предложения).""",
            ),
        )

        logger.info("✅ Face ID Registration Agent инициализирован")
        self.is_running = True

    async def start_registration_dialog(self, user_name: Optional[str] = None) -> str:
        """
        Начать диалог регистрации

        Args:
            user_name: Если известно имя, можно передать сразу

        Returns:
            Имя пользователя (слово "PHOTOBOOTH_START" можно перехватить)
        """
        try:
            if not self.session:
                await self.init()

            # Начальное приветствие
            prompt = "Привет! Новый пользователь хочет зарегистрироваться. "
            if user_name:
                prompt += f"Его имя: {user_name}. Попроси его встать перед камерой и начни фотосессию."
            else:
                prompt += "Пожалуйста, представься и попроси его имя."

            await self.session.send_realtime_input(
                text=prompt
            )

            # Получить ответ
            response = ""
            async for event in self.session.receive():
                if hasattr(event, "server_content"):
                    if event.server_content.turn_complete:
                        break
                    if hasattr(event.server_content, "text") and event.server_content.text:
                        response += event.server_content.text

            logger.debug(f"Agent response: {response}")
            return response

        except Exception as e:
            logger.error(f"❌ Ошибка в диалоге регистрации: {e}")
            return ""

    async def ask_for_name(self) -> str:
        """
        Попросить имя пользователя у агента

        Returns:
            Имя пользователя (распознанное из контекста)
        """
        try:
            await self.session.send_realtime_input(
                text="Теперь пожалуйста скажи свое имя. Просто произнеси его в микрофон."
            )

            response = ""
            async for event in self.session.receive():
                if hasattr(event, "server_content"):
                    if event.server_content.turn_complete:
                        break
                    if hasattr(event.server_content, "text") and event.server_content.text:
                        response += event.server_content.text

            # Нужно распарсить имя из ответа (это может быть транскрипция)
            logger.debug(f"Name response: {response}")
            return response.strip()

        except Exception as e:
            logger.error(f"❌ Ошибка при запросе имени: {e}")
            return "Unknown"

    async def request_photobooth(self) -> str:
        """
        Запросить photobooth session для захвата фото

        Returns:
            Инструкция для фотосессии
        """
        try:
            instruction = """Отлично! Сейчас мы сделаем несколько фото для запоминания.
Пожалуйста, смотри прямо на камеру, постарайся выглядеть естественно.
Я буду делать снимки. Готов? PHOTOBOOTH_START"""

            await self.session.send_realtime_input(
                text=instruction
            )

            response = ""
            async for event in self.session.receive():
                if hasattr(event, "server_content"):
                    if event.server_content.turn_complete:
                        break
                    if hasattr(event.server_content, "text") and event.server_content.text:
                        response += event.server_content.text

            return response

        except Exception as e:
            logger.error(f"❌ Ошибка при запросе photobooth: {e}")
            return "PHOTOBOOTH_START"

    async def finalize_registration(self, user_name: str) -> str:
        """
        Завершить регистрацию и поздравить пользователя

        Args:
            user_name: Имя зарегистрированного пользователя
        """
        try:
            message = f"""PHOTOBOOTH_DONE

Отлично, {user_name}! Я запомнил твое лицо. Теперь я всегда буду тебя узнавать!
Добро пожаловать в мою базу! 🐙✨"""

            await self.session.send_realtime_input(
                text=message
            )

            response = ""
            async for event in self.session.receive():
                if hasattr(event, "server_content"):
                    if event.server_content.turn_complete:
                        break
                    if hasattr(event.server_content, "text") and event.server_content.text:
                        response += event.server_content.text

            logger.info(f"✅ Пользователь {user_name} успешно зарегистрирован")
            return response

        except Exception as e:
            logger.error(f"❌ Ошибка при завершении регистрации: {e}")
            return ""

    async def close(self):
        """Закрыть сессию агента"""
        if self.session:
            await self.session.close()
            self.is_running = False
            logger.info("Face ID Registration Agent закрыт")


# Глобальный экземпляр агента
_registration_agent: Optional[FaceIDRegistrationAgent] = None


async def get_registration_agent() -> FaceIDRegistrationAgent:
    """Получить глобальный экземпляр агента регистрации"""
    global _registration_agent
    if _registration_agent is None:
        _registration_agent = FaceIDRegistrationAgent()
    return _registration_agent
