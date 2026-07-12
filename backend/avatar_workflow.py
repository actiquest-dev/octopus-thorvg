"""
Avatar Workflow Coordinator
Управляет полным сценарием работы аватара с Face ID

Sequence:
1. Camera starts → Detect faces
2. Face found in DB → Greet with user name
3. Face not found → Start registration flow
4. Get user name (voice) → Request photobooth
5. Capture 3-5 photos → Average embeddings → Save to DB
6. Welcome registered user → Continue conversation
"""

import asyncio
import logging
import time
from typing import Optional, Dict, List, Callable
from enum import Enum
import base64

from face_detector import FaceDetector
from face_db_postgres import get_face_database, FaceDatabasePostgres
from face_id_agent import get_registration_agent, FaceIDRegistrationAgent

logger = logging.getLogger(__name__)


class AvatarState(Enum):
    """States of avatar interaction"""
    IDLE = "idle"
    DETECTING_FACE = "detecting_face"
    IDENTIFIED = "identified"
    REGISTERING = "registering"
    PHOTOBOOTH = "photobooth"
    COMPLETE = "complete"


class AvatarWorkflow:
    """
    Координирует все действия аватара при запуске камеры
    """

    def __init__(self):
        self.state = AvatarState.IDLE
        self.current_user_id: Optional[str] = None
        self.current_user_name: Optional[str] = None
        self.face_detector = FaceDetector()
        self.registration_agent: Optional[FaceIDRegistrationAgent] = None
        self.face_db: Optional[FaceDatabasePostgres] = None

        # Callbacks для WebSocket синхронизации
        self.on_state_change: Optional[Callable] = None
        self.on_user_identified: Optional[Callable] = None
        self.on_registration_start: Optional[Callable] = None
        self.on_photobooth_trigger: Optional[Callable] = None

        # Для photobooth
        self.photobooth_frames: List[Dict] = []
        self.photobooth_active = False

    async def init(self):
        """Инициализировать workflow"""
        self.face_db = await get_face_database()
        self.registration_agent = await get_registration_agent()
        logger.info("✅ Avatar Workflow инициализирован")

    async def process_frame(self, jpeg_bytes: bytes, frame_id: int = 0) -> Dict:
        """
        Обработать видео-кадр

        Главная точка входа для каждого кадра с камеры

        Args:
            jpeg_bytes: JPEG данные кадра
            frame_id: ID кадра для отслеживания

        Returns:
            Результат обработки {state, user_id, user_name, action, confidence}
        """
        try:
            result = {
                "frame_id": frame_id,
                "state": self.state.value,
                "user_id": None,
                "user_name": None,
                "action": None,
                "confidence": None,
                "timestamp": time.time()
            }

            # PHOTOBOOTH режим - просто собираем кадры
            if self.photobooth_active:
                await self._process_photobooth_frame(jpeg_bytes, result)
                return result

            # Обычный режим - детектируем и идентифицируем
            faces = await self.face_detector.detect_faces_from_base64(
                base64.b64encode(jpeg_bytes).decode()
            )

            if not faces:
                result["action"] = "no_face"
                return result

            # Есть лицо - получить embedding
            face = faces[0]
            embedding = face.get("embedding")

            if not embedding:
                logger.warning("⚠️ Не удалось получить embedding из лица")
                return result

            # Попытаться идентифицировать
            user = await self.face_db.find_user_by_face(
                embedding,
                threshold=0.6
            )

            if user:
                # ЛИЦО НАЙДЕНО в БД ✅
                await self._handle_user_identified(user, result)
            else:
                # ЛИЦО НЕ НАЙДЕНО - начать регистрацию
                if self.state != AvatarState.REGISTERING:
                    await self._handle_unknown_face(result)

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке кадра: {e}")
            return {
                "frame_id": frame_id,
                "state": self.state.value,
                "error": str(e),
                "timestamp": time.time()
            }

    async def _handle_user_identified(self, user: Dict, result: Dict):
        """
        Пользователь идентифицирован - используется из БД

        Args:
            user: {user_id, name, confidence, matched_profile_id}
            result: Результат обработки для заполнения
        """
        self.current_user_id = user["user_id"]
        self.current_user_name = user["name"]
        confidence = user["confidence"]

        # Смена состояния только если это новый пользователь
        if self.state != AvatarState.IDENTIFIED:
            old_state = self.state
            self.state = AvatarState.IDENTIFIED

            # Сообщить аватару о новом пользователе
            result["action"] = "greet_user"
            result["user_id"] = self.current_user_id
            result["user_name"] = self.current_user_name
            result["confidence"] = confidence

            logger.info(f"✅ Идентифицирован пользователь: {self.current_user_name} (confidence: {confidence:.2f})")

            # Callback для WebSocket
            if self.on_user_identified:
                await self.on_user_identified({
                    "user_id": self.current_user_id,
                    "user_name": self.current_user_name,
                    "confidence": confidence
                })

            # Callback для смены состояния
            if self.on_state_change:
                await self.on_state_change(old_state, self.state)
        else:
            result["action"] = "continue"
            result["user_id"] = self.current_user_id
            result["user_name"] = self.current_user_name

    async def _handle_unknown_face(self, result: Dict):
        """
        Неизвестное лицо - начать регистрацию

        Args:
            result: Результат обработки для заполнения
        """
        old_state = self.state
        self.state = AvatarState.REGISTERING

        result["action"] = "start_registration"

        logger.info("🆕 Обнаружено новое лицо - запуск регистрации")

        # Callback для начала регистрации
        if self.on_registration_start:
            await self.on_registration_start()

        if self.on_state_change:
            await self.on_state_change(old_state, self.state)

        # Запустить диалог регистрации в фоне (не блокируем)
        asyncio.create_task(self._run_registration_flow())

    async def _run_registration_flow(self):
        """
        Полный flow регистрации нового пользователя

        Runs in background, non-blocking
        """
        try:
            logger.info("🔄 Начало flow регистрации...")

            # 1️⃣ Приветствие и запрос имени
            agent = self.registration_agent
            await agent.start_registration_dialog()

            # Даем пользователю время ответить (5 секунд)
            await asyncio.sleep(2)

            # 2️⃣ Получить имя (это будет транскрипция из Gemini)
            user_name = await agent.ask_for_name()

            if not user_name or user_name.lower() in ["unknown", "не могу"]:
                user_name = f"User_{int(time.time())}"

            self.current_user_name = user_name
            logger.info(f"📝 Имя пользователя: {user_name}")

            # 3️⃣ Запросить photobooth режим
            await agent.request_photobooth()
            await asyncio.sleep(1)

            # 4️⃣ Активировать photobooth - собрать 3-5 кадров
            old_state = self.state
            self.state = AvatarState.PHOTOBOOTH

            if self.on_photobooth_trigger:
                await self.on_photobooth_trigger({
                    "user_name": user_name,
                    "frames_needed": 5
                })

            if self.on_state_change:
                await self.on_state_change(old_state, self.state)

            # Ждем сбора фотографий (максимум 10 секунд)
            max_wait = 10
            wait_time = 0
            while len(self.photobooth_frames) < 5 and wait_time < max_wait:
                await asyncio.sleep(0.5)
                wait_time += 0.5

            if len(self.photobooth_frames) < 3:
                logger.warning(f"⚠️ Собрано только {len(self.photobooth_frames)} фото, нужно минимум 3")

            # 5️⃣ Обработать фотографии - усреднить embeddings
            if self.photobooth_frames:
                await self._process_photobooth_embeddings(user_name)

            # 6️⃣ Завершить регистрацию
            await agent.finalize_registration(user_name)

            # Перейти в состояние IDENTIFIED
            old_state = self.state
            self.state = AvatarState.IDENTIFIED

            if self.on_state_change:
                await self.on_state_change(old_state, self.state)

            logger.info(f"✅ Регистрация завершена: {user_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка в flow регистрации: {e}")
            self.state = AvatarState.IDLE

    async def _process_photobooth_frame(self, jpeg_bytes: bytes, result: Dict):
        """
        Обработать кадр в режиме photobooth

        Собрать кадры и embeddings для усреднения
        """
        try:
            # Детектировать лицо
            faces = await self.face_detector.detect_faces_from_base64(
                base64.b64encode(jpeg_bytes).decode()
            )

            if not faces:
                return

            face = faces[0]
            embedding = face.get("embedding")

            if embedding:
                self.photobooth_frames.append({
                    "embedding": embedding,
                    "timestamp": time.time(),
                    "frame_data": jpeg_bytes
                })

                result["action"] = "photobooth_capture"
                result["photobooth_count"] = len(self.photobooth_frames)

                logger.debug(f"📷 Photobooth: захвачен кадр {len(self.photobooth_frames)}")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки photobooth кадра: {e}")

    async def _process_photobooth_embeddings(self, user_name: str):
        """
        Усреднить embeddings из всех собранных кадров и зарегистрировать пользователя

        Args:
            user_name: Имя пользователя
        """
        try:
            import numpy as np

            if not self.photobooth_frames:
                logger.error("❌ Нет кадров для обработки")
                return

            # Усреднить embeddings
            embeddings = [f["embedding"] for f in self.photobooth_frames]
            embeddings_array = np.array(embeddings, dtype=np.float32)
            averaged_embedding = np.mean(embeddings_array, axis=0).tolist()

            # Зарегистрировать в БД
            result = await self.face_db.register_new_user(
                name=user_name,
                embedding=averaged_embedding,
                profile_data={
                    "registration_time": time.time(),
                    "photobooth_frames_count": len(self.photobooth_frames),
                    "method": "photobooth"
                }
            )

            self.current_user_id = result["user_id"]

            logger.info(f"✅ Пользователь {user_name} зарегистрирован в БД с ID {self.current_user_id}")
            logger.info(f"📊 Усреднено embeddings из {len(self.photobooth_frames)} кадров")

            # Очистить буфер
            self.photobooth_frames = []
            self.photobooth_active = False

        except Exception as e:
            logger.error(f"❌ Ошибка обработки embeddings: {e}")

    async def start_photobooth(self):
        """Начать режим photobooth"""
        self.photobooth_active = True
        self.photobooth_frames = []
        logger.info("📷 Photobooth активирован")

    async def stop_photobooth(self):
        """Остановить режим photobooth"""
        self.photobooth_active = False
        logger.info(f"📷 Photobooth остановлен ({len(self.photobooth_frames)} кадров)")

    async def reset(self):
        """Сбросить состояние аватара"""
        self.state = AvatarState.IDLE
        self.current_user_id = None
        self.current_user_name = None
        self.photobooth_active = False
        self.photobooth_frames = []
        logger.info("🔄 Workflow сброшен")

    def get_state(self) -> Dict:
        """Получить текущее состояние"""
        return {
            "state": self.state.value,
            "user_id": self.current_user_id,
            "user_name": self.current_user_name,
            "photobooth_active": self.photobooth_active,
            "photobooth_frames": len(self.photobooth_frames)
        }


# Глобальный экземпляр workflow'а
_avatar_workflow: Optional[AvatarWorkflow] = None


async def get_avatar_workflow() -> AvatarWorkflow:
    """Получить глобальный экземпляр workflow'а"""
    global _avatar_workflow
    if _avatar_workflow is None:
        _avatar_workflow = AvatarWorkflow()
        await _avatar_workflow.init()
    return _avatar_workflow
