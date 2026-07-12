"""
Voice Registration Service
Полная голосовая регистрация через аватар:
1. Аватар здоровается
2. Просит представиться
3. Получает имя голосом
4. Просит сделать фото лица
5. Сохраняет профиль
6. Переходит в режим приветствия
"""

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from typing import Optional, Dict, Any
from datetime import datetime

from user_profile_service import UserProfileService
from face_user_repository import FaceUserRepository
from gemini_integration import GeminiService
from models import User
import uuid


class VoiceRegistrationService:
    """Сервис для голосовой регистрации новых пользователей"""

    REGISTRATION_STAGES = {
        "greeting": 0,           # Аватар здоровается
        "ask_name": 1,           # Просит представиться
        "receive_name": 2,       # Получает имя голосом
        "ask_for_photo": 3,      # Просит сделать фото
        "process_face": 4,       # Обрабатывает фото
        "confirmation": 5,       # Подтверждает регистрацию
        "completed": 6           # Завершено
    }

    def __init__(self, db_session: AsyncSession, gemini_service: Optional[GeminiService] = None):
        self.db = db_session
        self.profile_service = UserProfileService(db_session)
        self.gemini_service = gemini_service or GeminiService()
        self.current_registrations = {}  # Отслеживание процессов регистрации

    async def start_registration_flow(self) -> Dict[str, Any]:
        """
        Начать процесс регистрации

        Returns:
            {
              "registration_id": "session-uuid",
              "stage": "greeting",
              "audio_greeting": "Привет! Давай знакомиться...",
              "next_action": "listen_for_name"
            }
        """
        try:
            registration_id = str(uuid.uuid4())
            logger.info(f"🎤 Начинаю регистрацию: {registration_id}")

            # Инициализировать сессию регистрации
            self.current_registrations[registration_id] = {
                "stage": 0,  # "greeting"
                "name": None,
                "face_data": None,
                "user_id": None,
                "created_at": datetime.utcnow()
            }

            # Сгенерировать приветствие
            greeting = await self.gemini_service.generate_response(
                query="""Ты аватар, который помогает новым людям регистрироваться.
                Дай ОЧЕНЬ КОРОТКОЕ (2 предложения) приветствие для новичка.
                Представься и попроси его рассказать своё имя.""",
                user_name="New Friend",
                user_context="",
                user_profile={}
            )

            result = {
                "registration_id": registration_id,
                "stage": "greeting",
                "audio_greeting": greeting,
                "next_action": "listen_for_name",
                "instructions": "Слушай приветствие аватара и скажи своё имя"
            }

            logger.info(f"✅ Регистрация инициирована: {registration_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка инициации регистрации: {e}")
            return {"error": str(e)}

    async def process_voice_input(
        self,
        registration_id: str,
        voice_text: str
    ) -> Dict[str, Any]:
        """
        Обработать голосовой ввод на текущем этапе

        Args:
            registration_id: ID сессии регистрации
            voice_text: Транскрипция голоса (от speech-to-text)

        Returns:
            Следующий этап или ошибка
        """
        try:
            if registration_id not in self.current_registrations:
                logger.warning(f"❌ Регистрация не найдена: {registration_id}")
                return {"error": "Registration not found"}

            reg_data = self.current_registrations[registration_id]
            current_stage = reg_data["stage"]

            logger.info(f"🎤 Обработка ввода: stage={current_stage}, text='{voice_text}'")

            # === STAGE 1: Ask Name → Receive Name ===
            if current_stage == self.REGISTRATION_STAGES["ask_name"]:
                # Пользователь произнёс свое имя
                name = self._extract_name_from_voice(voice_text)

                if not name or len(name) < 2:
                    # Попросить повторить
                    return {
                        "registration_id": registration_id,
                        "stage": "ask_name",
                        "audio_response": "Извини, не услышала. Можешь повторить своё имя?",
                        "next_action": "listen_for_name"
                    }

                reg_data["name"] = name
                reg_data["stage"] = self.REGISTRATION_STAGES["ask_for_photo"]

                # Сгенерировать ответ с подтверждением имени
                confirmation_prompt = f"""Пользователь только что сказал, что его зовут {name}.
                Дай КОРОТКИЙ (1 предложение) ответ с подтверждением имени и просьбой сделать фото лица.
                Будь дружелюбным и весёлым!"""

                response = await self.gemini_service.generate_response(
                    query=confirmation_prompt,
                    user_name=name,
                    user_context="",
                    user_profile={}
                )

                logger.info(f"✅ Имя получено: {name}")
                return {
                    "registration_id": registration_id,
                    "stage": "ask_for_photo",
                    "confirmed_name": name,
                    "audio_response": response,
                    "next_action": "capture_face",
                    "instructions": "Нажми кнопку и сделай фото своего лица"
                }

            # === STAGE 3: Ask Photo → Process Face ===
            elif current_stage == self.REGISTRATION_STAGES["ask_for_photo"]:
                # На этом этапе нужна фотография, не голос
                return {
                    "error": "Expected face photo, not voice input",
                    "next_action": "capture_face"
                }

            else:
                return {
                    "error": f"Unexpected stage: {current_stage}",
                    "current_stage": current_stage
                }

        except Exception as e:
            logger.error(f"❌ Ошибка обработки голоса: {e}")
            return {"error": str(e)}

    async def process_face_photo(
        self,
        registration_id: str,
        face_image_data: bytes
    ) -> Dict[str, Any]:
        """
        Обработать фото лица

        Args:
            registration_id: ID сессии регистрации
            face_image_data: Бинарные данные изображения

        Returns:
            Результат обработки или ошибка
        """
        try:
            if registration_id not in self.current_registrations:
                logger.warning(f"❌ Регистрация не найдена: {registration_id}")
                return {"error": "Registration not found"}

            reg_data = self.current_registrations[registration_id]

            if reg_data["stage"] != self.REGISTRATION_STAGES["ask_for_photo"]:
                return {
                    "error": f"Face photo not expected at stage {reg_data['stage']}"
                }

            logger.info(f"📸 Обрабатываю фото для {registration_id}")

            # Импортировать сервис распознавания
            from face_recognition_service import FaceRecognitionService
            face_service = FaceRecognitionService()

            # Извлечь embedding
            result = face_service.extract_face_embedding(face_image_data)
            if not result:
                return {
                    "registration_id": registration_id,
                    "stage": "ask_for_photo",
                    "error": "Лицо не найдено на фото",
                    "audio_response": "Я не вижу твоё лицо. Давай попробуем ещё раз? Убедись, что лицо хорошо видно!",
                    "next_action": "capture_face"
                }

            embedding, quality_score, image_hash = result

            if quality_score < 0.5:
                return {
                    "registration_id": registration_id,
                    "stage": "ask_for_photo",
                    "error": f"Качество низкое: {quality_score:.2f}",
                    "audio_response": "Качество фото не очень. Давай сделаем лучше!",
                    "next_action": "capture_face"
                }

            # Сохранить данные
            reg_data["face_data"] = {
                "embedding": embedding,
                "quality_score": quality_score,
                "image_hash": image_hash,
                "image_data": face_image_data
            }
            reg_data["stage"] = self.REGISTRATION_STAGES["confirmation"]

            logger.info(f"✅ Лицо обработано: quality={quality_score:.2f}")

            return {
                "registration_id": registration_id,
                "stage": "confirmation",
                "quality_score": quality_score,
                "audio_response": "Отлично! Твоё лицо записано. Сейчас я создам твой профиль!",
                "next_action": "confirm_registration"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка обработки фото: {e}")
            return {"error": str(e)}

    async def complete_registration(
        self,
        registration_id: str
    ) -> Dict[str, Any]:
        """
        Завершить регистрацию и создать пользователя

        Args:
            registration_id: ID сессии регистрации

        Returns:
            {user_id, greeting, status}
        """
        try:
            if registration_id not in self.current_registrations:
                logger.warning(f"❌ Регистрация не найдена: {registration_id}")
                return {"error": "Registration not found"}

            reg_data = self.current_registrations[registration_id]

            if not reg_data["name"] or not reg_data["face_data"]:
                return {"error": "Incomplete registration data"}

            logger.info(f"✅ Завершаю регистрацию: {registration_id}")

            # === 1. Создать пользователя ===
            repo = FaceUserRepository(self.db)
            user = await repo.create_user(
                name=reg_data["name"],
                profile_data={
                    "registration_date": datetime.utcnow().isoformat(),
                    "voice_registered": True
                }
            )
            reg_data["user_id"] = user.id

            # === 2. Зарегистрировать лицо ===
            face_data = reg_data["face_data"]
            await repo.add_face_profile(
                user_id=user.id,
                embedding=face_data["embedding"],
                quality_score=face_data["quality_score"],
                image_data=face_data["image_data"],
                image_hash=face_data["image_hash"],
                confidence=0.95
            )

            await repo.commit()

            # === 3. Сгенерировать приветствие ===
            greeting_text = f"""Готово! Я создала твой профиль, {reg_data['name']}!

Теперь я буду тебя узнавать по лицу и помнить все наши разговоры.
Рада познакомиться! Чем я могу тебе помочь?"""

            reg_data["stage"] = self.REGISTRATION_STAGES["completed"]

            logger.info(f"✅ Регистрация завершена: user_id={user.id}")

            result = {
                "status": "completed",
                "registration_id": registration_id,
                "user_id": user.id,
                "user_name": reg_data["name"],
                "audio_greeting": greeting_text,
                "next_mode": "avatar_mode",
                "instructions": "Теперь аватар в режиме приветствия готов с тобой общаться!"
            }

            # Очистить регистрацию
            del self.current_registrations[registration_id]

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка завершения регистрации: {e}")
            await self.db.rollback()
            return {"error": str(e)}

    def _extract_name_from_voice(self, voice_text: str) -> Optional[str]:
        """
        Извлечь имя из голосового ввода

        Args:
            voice_text: Текст от speech-to-text

        Returns:
            Извлечённое имя или None
        """
        # Простая логика: первое слово, начинающееся с заглавной буквы
        words = voice_text.strip().split()

        for word in words:
            if len(word) > 1 and word[0].isupper():
                # Очистить от пунктуации
                name = word.strip('.,!?;:"')
                if name.isalpha():
                    return name.capitalize()

        # Если ничего не нашли, вернуть первое слово
        if words:
            return words[0].strip('.,!?;:"').capitalize()

        return None

    async def get_registration_status(self, registration_id: str) -> Dict[str, Any]:
        """Получить текущий статус регистрации"""
        if registration_id not in self.current_registrations:
            return {"error": "Registration not found"}

        reg_data = self.current_registrations[registration_id]
        stage_name = [k for k, v in self.REGISTRATION_STAGES.items() if v == reg_data["stage"]][0]

        return {
            "registration_id": registration_id,
            "stage": stage_name,
            "stage_number": reg_data["stage"],
            "name": reg_data.get("name"),
            "has_face": reg_data["face_data"] is not None,
            "created_at": reg_data["created_at"].isoformat()
        }

    async def cancel_registration(self, registration_id: str) -> Dict[str, Any]:
        """Отменить регистрацию"""
        if registration_id in self.current_registrations:
            del self.current_registrations[registration_id]
            logger.info(f"❌ Регистрация отменена: {registration_id}")
            return {"status": "cancelled"}
        return {"error": "Registration not found"}
