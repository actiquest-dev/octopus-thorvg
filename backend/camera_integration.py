"""
Camera Integration Layer
Интегрирует Avatar Workflow в камеру и WebSocket синхронизацию

Основные функции:
- Обработка кадров с камеры
- Синхронизация с avatar_workflow
- Отправка команд аватару через WebSocket
- Управление photobooth сессиями
"""

import asyncio
import logging
from typing import Callable, Optional, Dict
import base64

from avatar_workflow import get_avatar_workflow, AvatarState
from timeline_sync import get_timeline_sync

logger = logging.getLogger(__name__)


class CameraIntegration:
    """
    Интегрирует обработку видео с управлением аватаром
    """

    def __init__(self):
        self.workflow = None
        self.timeline_sync = None
        self.is_camera_active = False
        self.frame_count = 0

        # Callbacks
        self.on_avatar_action: Optional[Callable] = None

    async def init(self):
        """Инициализировать интеграцию"""
        self.workflow = await get_avatar_workflow()
        self.timeline_sync = await get_timeline_sync()

        # Подключить callbacks
        self.workflow.on_state_change = self._on_workflow_state_change
        self.workflow.on_user_identified = self._on_user_identified
        self.workflow.on_registration_start = self._on_registration_start
        self.workflow.on_photobooth_trigger = self._on_photobooth_trigger

        logger.info("✅ Camera Integration инициализирован")

    async def on_camera_frame(self, jpeg_bytes: bytes, timestamp: float = 0):
        """
        Обработать новый кадр с камеры

        Вызывается ~1 раз в секунду из gemini_live_client

        Args:
            jpeg_bytes: JPEG данные
            timestamp: Временная метка кадра
        """
        if not self.is_camera_active:
            return

        try:
            self.frame_count += 1

            # Обработать через workflow
            result = await self.workflow.process_frame(jpeg_bytes, self.frame_count)

            # Отправить результаты в timeline-sync для фронтенда
            await self._send_timeline_update(result)

            # Если есть action, выполнить его
            if result.get("action"):
                await self._handle_action(result)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки кадра: {e}")

    async def camera_start(self):
        """Запустить обработку видео"""
        self.is_camera_active = True
        self.frame_count = 0

        await self.workflow.reset()

        logger.info("📷 Камера запущена - начало обработки видео")

        # Отправить на фронтенд
        await self.timeline_sync.send_message({
            "type": "camera_started",
            "timestamp": asyncio.get_event_loop().time()
        })

    async def camera_stop(self):
        """Остановить обработку видео"""
        self.is_camera_active = False

        logger.info(f"📷 Камера остановлена (обработано {self.frame_count} кадров)")

        # Отправить на фронтенд
        await self.timeline_sync.send_message({
            "type": "camera_stopped",
            "timestamp": asyncio.get_event_loop().time()
        })

    async def _send_timeline_update(self, result: Dict):
        """
        Отправить обновление статуса Face ID в timeline-sync

        Args:
            result: Результат обработки кадра
        """
        try:
            message = {
                "type": "face_detection",
                "frame_id": result.get("frame_id"),
                "state": result.get("state"),
                "action": result.get("action"),
                "user_id": result.get("user_id"),
                "user_name": result.get("user_name"),
                "confidence": result.get("confidence"),
                "timestamp": result.get("timestamp")
            }

            # Только отправлять важные обновления (экономим трафик)
            if result.get("action") and result["action"] != "continue":
                await self.timeline_sync.send_message(message)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки timeline update: {e}")

    async def _handle_action(self, result: Dict):
        """
        Обработать action из workflow

        Args:
            result: Результат обработки с action
        """
        action = result.get("action")

        if action == "greet_user":
            # Пользователь идентифицирован - приветствие
            user_name = result.get("user_name", "Friend")
            confidence = result.get("confidence", 0)

            avatar_cmd = {
                "type": "action",
                "action": "greet",
                "user_name": user_name,
                "confidence": confidence,
                "message": f"Привет, {user_name}! Рад тебя видеть! 🐙"
            }

            await self.timeline_sync.send_message(avatar_cmd)

        elif action == "start_registration":
            # Новое лицо - начать регистрацию
            avatar_cmd = {
                "type": "action",
                "action": "say",
                "message": "Привет! Я тебя не знаю. Давай я внесу тебя в базу! Как тебя зовут?"
            }

            await self.timeline_sync.send_message(avatar_cmd)

        elif action == "photobooth_capture":
            # Photobooth захватывает кадр
            photobooth_count = result.get("photobooth_count", 0)

            avatar_cmd = {
                "type": "action",
                "action": "photobooth_frame",
                "frame_number": photobooth_count,
                "total_frames": 5
            }

            await self.timeline_sync.send_message(avatar_cmd)

    async def _on_workflow_state_change(self, old_state, new_state):
        """Callback: смена состояния workflow'а"""
        logger.info(f"🔄 State change: {old_state.value} → {new_state.value}")

        message = {
            "type": "workflow_state_changed",
            "old_state": old_state.value,
            "new_state": new_state.value,
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.timeline_sync.send_message(message)

    async def _on_user_identified(self, user_info: Dict):
        """Callback: пользователь идентифицирован"""
        logger.info(f"✅ User identified: {user_info}")

        # Уже обработано в _handle_action, но можно добавить логику
        await self.timeline_sync.send_message({
            "type": "user_identified",
            "user_id": user_info.get("user_id"),
            "user_name": user_info.get("user_name"),
            "confidence": user_info.get("confidence")
        })

    async def _on_registration_start(self):
        """Callback: начало регистрации"""
        logger.info("🆕 Registration started")

        await self.timeline_sync.send_message({
            "type": "registration_started",
            "message": "Starting new user registration..."
        })

    async def _on_photobooth_trigger(self, config: Dict):
        """Callback: photobooth запущен"""
        user_name = config.get("user_name", "New User")
        frames_needed = config.get("frames_needed", 5)

        logger.info(f"📷 Photobooth triggered for {user_name} ({frames_needed} frames)")

        # Активировать photobooth в workflow
        await self.workflow.start_photobooth()

        # Отправить команду на фронтенд
        await self.timeline_sync.send_message({
            "type": "action",
            "action": "photobooth_start",
            "user_name": user_name,
            "frames_needed": frames_needed,
            "message": "📷 Теперь сделаю несколько фото для запоминания! Смотри в камеру и улыбнись!"
        })


# Глобальный экземпляр
_camera_integration: Optional[CameraIntegration] = None


async def get_camera_integration() -> CameraIntegration:
    """Получить глобальный экземпляр camera integration"""
    global _camera_integration
    if _camera_integration is None:
        _camera_integration = CameraIntegration()
        await _camera_integration.init()
    return _camera_integration
