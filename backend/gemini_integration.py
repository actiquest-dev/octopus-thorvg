"""
Gemini Integration Service
Интеграция с Google Gemini API и RAG контекстом
"""

import os
import google.generativeai as genai
from typing import Tuple, Optional, List
from loguru import logger
from datetime import datetime

# Конфигурация Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY не установлен в .env")


class GeminiService:
    """Сервис интеграции с Gemini"""

    def __init__(self):
        """Инициализировать Gemini"""
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
        logger.info("✅ GeminiService инициализирован")

    async def generate_response(
        self,
        query: str,
        user_name: str = "User",
        user_context: str = "",
        user_profile: Optional[dict] = None
    ) -> str:
        """
        Сгенерировать ответ от Gemini с контекстом пользователя

        Args:
            query: Вопрос/запрос от пользователя
            user_name: Имя пользователя (для персонализации)
            user_context: Контекст из RAG (предыдущие разговоры, документы)
            user_profile: Профиль пользователя (доп. контекст)

        Returns:
            Ответ от Gemini
        """
        if not self.model:
            logger.error("❌ Gemini модель не инициализирована")
            return "Ошибка: Gemini API недоступен"

        try:
            # Построить промпт с контекстом
            system_prompt = self._build_system_prompt(user_name, user_profile)
            full_context = self._build_full_context(query, user_context, user_profile)

            # Отправить запрос
            response = self.model.generate_content(
                f"{system_prompt}\n\n{full_context}\n\nПользователь: {query}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                )
            )

            answer = response.text
            logger.info(f"✅ Gemini ответ получен ({len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"❌ Ошибка Gemini запроса: {e}")
            return f"Ошибка при обработке запроса: {str(e)}"

    async def retrieve_rag_context(self, query: str, top_k: int = 3) -> Tuple[str, int]:
        """
        Получить релевантный контекст из RAG системы

        Args:
            query: Запрос для поиска контекста
            top_k: Количество документов для возврата

        Returns:
            (context_text: str, doc_count: int)
        """
        try:
            # TODO: Реализовать поиск в FalkorDB или Redis
            # Здесь нужна интеграция с вашей RAG системой
            # Например, используя embeddings из query и поиск похожих документов

            # Временно возвращаем пустой контекст
            logger.info(f"🔍 RAG поиск по запросу: {query}")
            return "", 0

        except Exception as e:
            logger.error(f"❌ Ошибка RAG поиска: {e}")
            return "", 0

    def _build_system_prompt(self, user_name: str, user_profile: Optional[dict]) -> str:
        """Построить системный промпт"""
        profile_info = ""
        if user_profile:
            profile_info = f"""
Информация о пользователе {user_name}:
{self._format_profile(user_profile)}
"""

        return f"""Ты - дружелюбный и полезный ассистент.
Текущее время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
{profile_info}

Отвечай на русском языке, будь вежлив и информативен.
"""

    def _build_full_context(
        self,
        query: str,
        rag_context: str,
        user_profile: Optional[dict]
    ) -> str:
        """Построить полный контекст для запроса"""
        context_parts = []

        if rag_context:
            context_parts.append(f"📚 Релевантная информация:\n{rag_context}")

        if user_profile and user_profile.get("recent_interactions"):
            interactions = user_profile.get("recent_interactions", [])
            if interactions:
                context_parts.append(f"📝 Недавние взаимодействия:\n{interactions}")

        if context_parts:
            return "\n\n".join(context_parts)
        return ""

    def _format_profile(self, profile: dict) -> str:
        """Форматировать профиль пользователя"""
        lines = []
        for key, value in profile.items():
            if isinstance(value, (str, int, float)):
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "Нет данных профиля"

    async def stream_response(
        self,
        query: str,
        user_name: str = "User"
    ):
        """
        Получить потоковый ответ (для реал-тайм)

        Args:
            query: Вопрос
            user_name: Имя пользователя

        Yields:
            Части ответа
        """
        if not self.model:
            yield "Ошибка: Gemini API недоступен"
            return

        try:
            prompt = f"Пользователь {user_name}: {query}"
            response = self.model.generate_content(
                prompt,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                )
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"❌ Ошибка потокового ответа: {e}")
            yield f"Ошибка: {str(e)}"

    async def analyze_user_emotion(self, text: str) -> str:
        """
        Анализировать эмоцию в тексте

        Args:
            text: Текст для анализа

        Returns:
            Определённая эмоция (happy, sad, angry, neutral, etc)
        """
        if not self.model:
            return "neutral"

        try:
            prompt = f"""Проанализируй эмоцию в следующем тексте.
Ответь одним словом: happy, sad, angry, neutral, confused, excited.

Текст: "{text}"

Ответ:"""

            response = self.model.generate_content(prompt)
            emotion = response.text.strip().lower()

            # Валидировать
            valid_emotions = ["happy", "sad", "angry", "neutral", "confused", "excited"]
            if emotion not in valid_emotions:
                emotion = "neutral"

            logger.info(f"😊 Эмоция определена: {emotion}")
            return emotion

        except Exception as e:
            logger.error(f"❌ Ошибка анализа эмоции: {e}")
            return "neutral"

    async def generate_user_summary(
        self,
        user_name: str,
        interactions: List[str],
        emotions: List[str]
    ) -> str:
        """
        Сгенерировать резюме пользователя на основе его взаимодействий

        Args:
            user_name: Имя пользователя
            interactions: Список последних взаимодействий
            emotions: Список эмоций

        Returns:
            Резюме пользователя
        """
        if not self.model:
            return "Резюме недоступно"

        try:
            prompt = f"""Напиши краткое резюме пользователя {user_name} на основе:

Последние взаимодействия:
{chr(10).join(f'- {i}' for i in interactions[-5:])}

Эмоции:
{', '.join(set(emotions[-5:]))}

Резюме должно быть 2-3 предложения, информативным и полезным для персонализации будущих взаимодействий."""

            response = self.model.generate_content(prompt)
            summary = response.text

            logger.info(f"📋 Резюме пользователя сгенерировано")
            return summary

        except Exception as e:
            logger.error(f"❌ Ошибка генерации резюме: {e}")
            return "Ошибка при генерации резюме"

    def get_model_info(self) -> dict:
        """Получить информацию о модели"""
        return {
            "model": "gemini-1.5-flash",
            "status": "active" if self.model else "inactive",
            "api_key_set": bool(GEMINI_API_KEY),
        }
