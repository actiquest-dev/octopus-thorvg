import asyncio
import os
import logging
from google import genai
from google.genai import types

# Импортировать Face ID модули
from face_detector import get_face_detector, detect_and_process_faces
from face_db import get_face_database

logger = logging.getLogger(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser("~/octopus-thorvg/credentials.json")

# Глобальная переменная для callback результатов Face ID
_face_id_callback = None

class UnifiedGeminiLive:
    """Одна сессия для audio + video стриминга с Face ID обработкой"""

    def __init__(self, face_id_callback=None):
        self.session = None
        self.client = None
        self.project_id = "upheld-rain-484209-a6"
        self.location = "global"
        self.model = "gemini-live-2.5-flash-native-audio"
        self.face_id_callback = face_id_callback  # Callback для результатов Face ID
        self.last_face_id_time = 0  # Для throttling Face ID обработки
        self.face_id_throttle_ms = 1000  # Обрабатывать не чаще чем 1 раз в секунду
        
    async def init(self):
        """Инициализировать Gemini Live сессию"""
        self.client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
        
        self.session = await self.client.aio.live.connect(
            model=self.model,
            config=types.LiveConnectConfig(
                response_modalities=["audio"],
                input_audio_transcription={},      # Включаем распознавание речи
                output_audio_transcription={},     # Включаем текст ответов
                enable_affective_dialog=True,
                system_instruction="Ты - веселый дружелюбный осьминог. Отвечай коротко и естественно.",
            ),
        )
        print("✅ Gemini Live сессия инициализирована")
    
    async def send_audio(self, audio_bytes):
        """Отправить audio chunk (16kHz PCM)"""
        if not self.session:
            await self.init()
        
        await self.session.send_realtime_input(
            audio=types.Blob(
                data=audio_bytes,
                mime_type='audio/pcm;rate=16000'
            )
        )
    
    async def send_video(self, jpeg_bytes):
        """
        Отправить video frame (JPEG) и параллельно обработать Face ID

        Face ID обработка происходит асинхронно и не блокирует отправку в Gemini
        """
        if not self.session:
            await self.init()

        # Отправить в Gemini API (основной поток)
        await self.session.send_realtime_input(
            multimedia=types.Blob(
                data=jpeg_bytes,
                mime_type='image/jpeg'
            )
        )

        # НОВОЕ: Параллельно обработать Face ID (не блокирует)
        # Throttling: обрабатываем не чаще 1 раза в секунду
        import time
        current_time = time.time() * 1000  # в миллисекундах

        if current_time - self.last_face_id_time >= self.face_id_throttle_ms:
            self.last_face_id_time = current_time
            # Запустить Face ID обработку в фоне
            asyncio.create_task(self._process_face_id_async(jpeg_bytes))

    async def _process_face_id_async(self, jpeg_bytes):
        """
        Обработать Face ID из JPEG кадра (асинхронно, не блокирует)

        1. Детектировать лица
        2. Получить embeddings
        3. Найти пользователя в БД
        4. Отправить результат через callback
        """
        try:
            import base64
            import logging

            logger.debug("🔄 Начало Face ID обработки...")

            # Конвертировать JPEG в base64
            image_b64 = base64.b64encode(jpeg_bytes).decode()

            # Шаг 1: Детектировать и обработать лица
            faces = await detect_and_process_faces(image_b64)

            if not faces:
                logger.debug("❌ Лиц не найдено в кадре")
                return

            logger.info(f"✅ Найдено {len(faces)} лиц(а)")

            # Получить БД
            db = await get_face_database()

            # Шаг 2: Для каждого лица попытаться найти пользователя
            for face in faces:
                embedding = face.get("embedding", [])
                if not embedding:
                    continue

                # Попытка найти пользователя по embedding
                match = await db.find_user_by_face(embedding, threshold=0.6)

                face_result = {
                    "face_id": face["face_id"],
                    "bbox": face["bbox"],
                    "confidence": face["confidence"],
                    "keypoints": face["keypoints"],
                    "user_match": match  # None или {user_id, name, confidence, ...}
                }

                logger.info(
                    f"📊 Результат Face ID: "
                    f"лицо={face['face_id']}, "
                    f"пользователь={match['name'] if match else 'не найден'}, "
                    f"confidence={match['confidence']:.2f if match else 0}"
                )

                # Вызвать callback если задан
                if self.face_id_callback:
                    try:
                        await self.face_id_callback(face_result)
                    except Exception as e:
                        logger.error(f"❌ Ошибка в Face ID callback: {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка при Face ID обработке: {e}", exc_info=True)
    
    async def receive_response(self):
        """Получить ответ от Gemini (генератор)"""
        if not self.session:
            return
        
        try:
            async for message in self.session.receive():
                result = self._process_message(message)
                if result:
                    yield result
        except Exception as e:
            print(f"❌ Ошибка при получении: {e}")
    
    def _process_message(self, message):
        """Обработать сообщение от Gemini"""
        result = {}
        
        if message.server_content:
            # INPUT_TRANSCRIPTION - что сказал пользователь
            if message.server_content.input_transcription:
                trans = message.server_content.input_transcription
                if trans.text:
                    result['type'] = 'input_transcription'
                    result['text'] = trans.text
                    result['finished'] = trans.finished or False
            
            # OUTPUT_TRANSCRIPTION - что ответит ИИ
            elif message.server_content.output_transcription:
                trans = message.server_content.output_transcription
                if trans.text:
                    result['type'] = 'output_transcription'
                    result['text'] = trans.text
                    result['finished'] = trans.finished or False
            
            # AUDIO - аудио ответ
            elif message.server_content.model_turn:
                for part in message.server_content.model_turn.parts:
                    if part.inline_data:
                        result['type'] = 'audio'
                        result['data'] = part.inline_data.data
            
            # TURN_COMPLETE - разговор завершен
            if message.server_content.turn_complete:
                result['turn_complete'] = True
        
        return result if result else None
    
    async def close(self):
        """Закрыть сессию"""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
            print("✅ Gemini Live сессия закрыта")