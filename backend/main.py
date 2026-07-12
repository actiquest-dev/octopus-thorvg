"""
FastAPI Main App
Face Recognition API + Gemini integration
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
from contextlib import asynccontextmanager
from loguru import logger
from typing import Optional

# Импорты
from database import init_db, close_db, init_redis, close_redis, get_db, redis_client, RedisCache, AsyncSessionLocal
from face_recognition_service import FaceRecognitionService
from face_user_repository import FaceUserRepository
from gemini_integration import GeminiService
from user_profile_service import UserProfileService
from avatar_greeting_service import AvatarGreetingService
from voice_registration_service import VoiceRegistrationService
from models import User, FaceProfile
from sqlalchemy.ext.asyncio import AsyncSession

# Конфигурация логирования
logger.add(
    "logs/face_id.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Сервисы (глобальные)
face_service: Optional[FaceRecognitionService] = None
gemini_service: Optional[GeminiService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle управления приложением"""
    # Startup
    logger.info("🚀 Запуск приложения Face Recognition API")
    try:
        # Инициализировать БД
        await init_db()

        # Инициализировать Redis
        await init_redis()

        # Инициализировать сервисы
        global face_service, gemini_service
        face_service = FaceRecognitionService()
        gemini_service = GeminiService()

        logger.info("✅ Все компоненты инициализированы")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Завершение работы приложения")
    await close_redis()
    await close_db()
    logger.info("✅ Приложение остановлено")


# Создать FastAPI приложение
app = FastAPI(
    title="Face Recognition API",
    description="API для распознавания лиц и интеграции с Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Schemas ===
from pydantic import BaseModel


class RegisterUserRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: Optional[str]
    created_at: str
    interaction_count: int


class IdentifyResponse(BaseModel):
    user_id: str
    name: str
    confidence: float
    distance: float


class GeminiQueryRequest(BaseModel):
    user_id: str
    query: str
    use_rag: bool = True


class GeminiQueryResponse(BaseModel):
    user_id: str
    query: str
    response: str
    context_docs: int


# === API Endpoints ===

@app.get("/health", tags=["Health"])
async def health_check():
    """Проверить здоровье API"""
    return {
        "status": "ok",
        "service": "Face Recognition API",
        "version": "1.0.0"
    }


@app.post("/api/users/register", response_model=UserResponse, tags=["Users"])
async def register_user(
    req: RegisterUserRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Зарегистрировать нового пользователя

    Требует:
    - name: Имя пользователя
    - email: Email (опционально)
    - phone: Телефон (опционально)
    """
    try:
        repo = FaceUserRepository(db, RedisCache(redis_client))
        user = await repo.create_user(
            name=req.name,
            email=req.email,
            phone=req.phone
        )
        await repo.commit()

        logger.info(f"✅ Пользователь зарегистрирован: {user.id}")
        return user.to_dict()

    except Exception as e:
        logger.error(f"❌ Ошибка регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/faces/register/{user_id}", tags=["Face Recognition"])
async def register_face(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Зарегистрировать лицо пользователя

    Требует:
    - user_id: ID пользователя
    - file: Изображение лица (JPG/PNG)
    """
    try:
        if not face_service:
            raise HTTPException(status_code=500, detail="Face service не инициализирован")

        # Прочитать файл
        image_data = await file.read()

        # Извлечь embedding
        result = face_service.extract_face_embedding(image_data)
        if not result:
            raise HTTPException(status_code=400, detail="Лицо не найдено или качество низкое")

        embedding, quality_score, image_hash = result

        # Сохранить в БД
        repo = FaceUserRepository(db, RedisCache(redis_client))
        face_profile = await repo.add_face_profile(
            user_id=user_id,
            embedding=embedding,
            quality_score=quality_score,
            image_hash=image_hash,
            image_data=image_data  # Опционально
        )
        await repo.commit()

        logger.info(f"✅ Лицо зарегистрировано для {user_id}")
        return {
            "status": "success",
            "face_profile_id": face_profile.id,
            "quality_score": quality_score,
            "embedding_size": len(embedding)
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации лица: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/faces/identify", response_model=IdentifyResponse, tags=["Face Recognition"])
async def identify_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Идентифицировать лицо пользователя

    Требует:
    - file: Изображение лица (JPG/PNG)

    Возвращает: user_id, name, confidence, distance
    """
    try:
        if not face_service:
            raise HTTPException(status_code=500, detail="Face service не инициализирован")

        # Прочитать файл
        image_data = await file.read()

        # Извлечь embedding
        result = face_service.extract_face_embedding(image_data)
        if not result:
            raise HTTPException(status_code=400, detail="Лицо не найдено")

        embedding, _, _ = result

        # Получить все embeddings для сравнения
        repo = FaceUserRepository(db, RedisCache(redis_client))
        stored_embeddings = await repo.get_all_face_embeddings()

        if not stored_embeddings:
            raise HTTPException(status_code=404, detail="Нет зарегистрированных лиц")

        # Найти совпадение
        match = face_service.find_best_match(embedding, stored_embeddings)
        if not match:
            raise HTTPException(status_code=404, detail="Совпадение не найдено")

        user_id, distance = match

        # Получить пользователя
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Увеличить счётчик
        await repo.increment_interaction_count(user_id)
        await repo.commit()

        # Посчитать confidence
        confidence = max(0.0, 1.0 - (distance / 1.0))

        logger.info(f"✅ Лицо идентифицировано: {user.name} (confidence: {confidence:.2f})")
        return {
            "user_id": user_id,
            "name": user.name,
            "confidence": confidence,
            "distance": distance
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка идентификации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/query", response_model=GeminiQueryResponse, tags=["Gemini"])
async def gemini_query(
    req: GeminiQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить запрос Gemini с контекстом пользователя

    Требует:
    - user_id: ID пользователя
    - query: Вопрос/запрос
    - use_rag: Использовать RAG контекст (default: True)
    """
    try:
        if not gemini_service:
            raise HTTPException(status_code=500, detail="Gemini service не инициализирован")

        # Получить пользователя
        repo = FaceUserRepository(db, RedisCache(redis_client))
        user = await repo.get_user_by_id(req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Получить контекст
        context = ""
        context_docs = 0

        if req.use_rag:
            # Получить контекст из RAG (нужно реализовать в gemini_integration.py)
            context, context_docs = await gemini_service.retrieve_rag_context(req.query)

        # Получить ответ от Gemini
        response = await gemini_service.generate_response(
            query=req.query,
            user_name=user.name,
            user_context=context,
            user_profile=user.profile_data
        )

        logger.info(f"✅ Gemini ответ для {user.name}")
        return {
            "user_id": req.user_id,
            "query": req.query,
            "response": response,
            "context_docs": context_docs
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка Gemini запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о пользователе"""
    try:
        repo = FaceUserRepository(db, RedisCache(redis_client))
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user.to_dict()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка получения пользователя: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === AVATAR GREETING ===

@app.post("/api/avatar/greeting", tags=["Avatar"])
async def get_avatar_greeting(
    user_id: str,
    confidence: float = 0.95,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить персонализированное приветствие аватара

    Аватар:
    - Узнаёт пользователя по лицу
    - Вспоминает его историю разговоров
    - Генерирует теплое приветствие
    - Предлагает продолжение разговора

    Args:
        user_id: ID пользователя
        confidence: Уверенность в распознавании (0-1)
    """
    try:
        greeting_service = AvatarGreetingService(db, gemini_service)
        greeting = await greeting_service.generate_greeting(user_id, confidence)

        logger.info(f"✅ Приветствие отправлено для {user_id}")
        return greeting

    except Exception as e:
        logger.error(f"❌ Ошибка приветствия: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/avatar/memories/{user_id}", tags=["Avatar"])
async def get_user_memories(
    user_id: str,
    max_memories: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить ключевые воспоминания пользователя

    Используется аватаром для вспоминания прошлых моментов

    Args:
        user_id: ID пользователя
        max_memories: Максимум воспоминаний
    """
    try:
        greeting_service = AvatarGreetingService(db, gemini_service)
        memories = await greeting_service.get_memory_recall(user_id, max_memories)

        logger.info(f"✅ Воспоминания загружены для {user_id}")
        return {
            "user_id": user_id,
            "memories": memories.get("memories", []),
            "personality": memories.get("personality", []),
            "primary_emotion": memories.get("primary_emotion", "neutral"),
            "key_topics": memories.get("topics", [])
        }

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки воспоминаний: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/profile/{user_id}", tags=["Users"])
async def get_full_profile(
    user_id: str,
    include_history: bool = True,
    history_limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить полный профиль пользователя со всей историей

    Загружает:
    - Основную информацию
    - Все зарегистрированные лица
    - Историю разговоров
    - Логирование действий
    - Резюме с ключевыми фактами

    Args:
        user_id: ID пользователя
        include_history: Загружать ли историю
        history_limit: Количество сообщений
    """
    try:
        profile_service = UserProfileService(db)
        profile = await profile_service.load_full_profile(
            user_id,
            include_history=include_history,
            history_limit=history_limit,
            include_actions=True
        )

        if not profile:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        logger.info(f"✅ Полный профиль загружен для {user_id}")
        return profile

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки профиля: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversation/save", tags=["Avatar"])
async def save_conversation_turn(
    user_id: str,
    role: str,
    content: str,
    emotion: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Сохранить сообщение в историю разговора

    Args:
        user_id: ID пользователя
        role: "user" или "assistant"
        content: Текст сообщения
        emotion: Определённая эмоция (happy, sad, angry, etc)
    """
    try:
        profile_service = UserProfileService(db)
        conversation = await profile_service.save_conversation_turn(
            user_id=user_id,
            role=role,
            content=content,
            emotion=emotion
        )
        await db.commit()

        if not conversation:
            raise HTTPException(status_code=400, detail="Не удалось сохранить сообщение")

        logger.info(f"✅ Сообщение сохранено для {user_id}")
        return {
            "status": "success",
            "conversation_id": conversation.id,
            "role": role
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === ГОЛОСОВАЯ РЕГИСТРАЦИЯ ===

@app.post("/api/register/voice/start", tags=["Voice Registration"])
async def start_voice_registration(db: AsyncSession = Depends(get_db)):
    """
    Начать процесс голосовой регистрации

    Returns:
    {
      "registration_id": "session-uuid",
      "stage": "greeting",
      "audio_greeting": "Привет! Давай знакомиться...",
      "next_action": "listen_for_name"
    }

    Аватар здоровается и просит пользователя представиться голосом
    """
    try:
        voice_service = VoiceRegistrationService(db, gemini_service)
        result = await voice_service.start_registration_flow()
        logger.info(f"🎤 Голосовая регистрация начата: {result.get('registration_id')}")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка начала регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/register/voice/process", tags=["Voice Registration"])
async def process_voice_input(
    registration_id: str,
    voice_text: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Обработать голосовой ввод на текущем этапе регистрации

    Args:
        registration_id: ID сессии регистрации (из /start)
        voice_text: Транскрипция голоса от speech-to-text (например, от Web Speech API)

    Returns:
    {
      "stage": "ask_for_photo",
      "confirmed_name": "Alice",
      "audio_response": "Отлично, Alice! Давай сделаем твоё фото...",
      "next_action": "capture_face"
    }
    """
    try:
        voice_service = VoiceRegistrationService(db, gemini_service)
        result = await voice_service.process_voice_input(registration_id, voice_text)
        logger.info(f"🎤 Голос обработан: {registration_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка обработки голоса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/register/voice/photo", tags=["Voice Registration"])
async def process_registration_photo(
    registration_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузить фото лица для голосовой регистрации

    Args:
        registration_id: ID сессии регистрации
        file: Фото лица (JPG/PNG)

    Returns:
    {
      "stage": "confirmation",
      "quality_score": 0.92,
      "audio_response": "Отлично! Сейчас создаю твой профиль...",
      "next_action": "confirm_registration"
    }
    """
    try:
        image_data = await file.read()

        voice_service = VoiceRegistrationService(db, gemini_service)
        result = await voice_service.process_face_photo(registration_id, image_data)

        logger.info(f"📸 Фото регистрации обработано: {registration_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обработки фото: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/register/voice/complete", tags=["Voice Registration"])
async def complete_voice_registration(
    registration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Завершить голосовую регистрацию и создать пользователя

    Returns:
    {
      "status": "completed",
      "user_id": "uuid",
      "user_name": "Alice",
      "audio_greeting": "Готово! Я создала твой профиль...",
      "next_mode": "avatar_mode"
    }

    После этого пользователь переходит в режим приветствия аватара
    """
    try:
        voice_service = VoiceRegistrationService(db, gemini_service)
        result = await voice_service.complete_registration(registration_id)

        logger.info(f"✅ Голосовая регистрация завершена: {registration_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка завершения регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/register/voice/status/{registration_id}", tags=["Voice Registration"])
async def get_registration_status(
    registration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить статус текущей регистрации"""
    try:
        voice_service = VoiceRegistrationService(db, gemini_service)
        status = await voice_service.get_registration_status(registration_id)
        return status
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/register/voice/cancel/{registration_id}", tags=["Voice Registration"])
async def cancel_registration(
    registration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Отменить голосовую регистрацию"""
    try:
        voice_service = VoiceRegistrationService(db, gemini_service)
        result = await voice_service.cancel_registration(registration_id)
        logger.info(f"❌ Регистрация отменена: {registration_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка отмены: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === WebSocket для реал-тайма ===

@app.websocket("/ws/avatar")
async def websocket_avatar_interaction(websocket: WebSocket):
    """
    WebSocket для реал-тайм взаимодействия с аватаром

    Поток данных:
    1. Браузер отправляет: {type: "identify", image: base64}
    2. Сервер: распознаёт, загружает профиль, генерирует приветствие
    3. Браузер отправляет: {type: "message", user_id: ..., text: "..."}
    4. Сервер: обрабатывает через Gemini, вспоминает историю
    """
    await websocket.accept()
    logger.info("📡 Avatar WebSocket клиент подключен")

    current_user_id = None

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            # === IDENTIFY: Распознавание лица ===
            if message_type == "identify":
                try:
                    image_base64 = data.get("image")
                    if not image_base64:
                        await websocket.send_json({"error": "Image required"})
                        continue

                    # Конвертировать из base64
                    import base64
                    image_data = base64.b64decode(image_base64)

                    # Получить сессию БД для каждого запроса
                    async with AsyncSessionLocal() as db:
                        # Распознать лицо
                        result = face_service.extract_face_embedding(image_data)
                        if not result:
                            await websocket.send_json({
                                "type": "identify_result",
                                "status": "no_face",
                                "message": "Лицо не найдено"
                            })
                            continue

                        embedding, quality_score, _ = result

                        # Найти совпадение
                        repo = FaceUserRepository(db, RedisCache(redis_client))
                        stored_embeddings = await repo.get_all_face_embeddings()
                        match = face_service.find_best_match(embedding, stored_embeddings)

                        if not match:
                            await websocket.send_json({
                                "type": "identify_result",
                                "status": "not_found",
                                "message": "Пользователь не распознан"
                            })
                            continue

                        user_id, distance = match
                        current_user_id = user_id
                        confidence = max(0.0, 1.0 - (distance / 1.0))

                        # Получить приветствие
                        greeting_service = AvatarGreetingService(db, gemini_service)
                        greeting = await greeting_service.generate_greeting(user_id, confidence)

                        # Отправить приветствие
                        await websocket.send_json({
                            "type": "identify_result",
                            "status": "success",
                            "user_id": user_id,
                            "greeting": greeting.get("greeting"),
                            "user_name": greeting.get("user_name"),
                            "confidence": confidence,
                            "times_met": greeting.get("times_met"),
                            "tone": greeting.get("tone"),
                            "suggestions": greeting.get("suggestions"),
                            "memories": greeting.get("memories")
                        })

                        # Увеличить счётчик
                        await repo.increment_interaction_count(user_id)
                        await db.commit()

                except Exception as e:
                    logger.error(f"❌ WebSocket identify ошибка: {e}")
                    await websocket.send_json({"error": str(e)})

            # === MESSAGE: Сообщение от пользователя ===
            elif message_type == "message":
                try:
                    if not current_user_id:
                        await websocket.send_json({"error": "User not identified"})
                        continue

                    user_message = data.get("text")
                    if not user_message:
                        await websocket.send_json({"error": "Message text required"})
                        continue

                    async with AsyncSessionLocal() as db:
                        profile_service = UserProfileService(db)

                        # Анализировать эмоцию (опционально)
                        emotion = await gemini_service.analyze_user_emotion(user_message)

                        # Сохранить сообщение пользователя
                        await profile_service.save_conversation_turn(
                            user_id=current_user_id,
                            role="user",
                            content=user_message,
                            emotion=emotion
                        )

                        # Получить контекст для ответа
                        user_summary = await profile_service.get_user_summary_for_llm(current_user_id)
                        conversation_context = await profile_service.get_conversation_context(
                            current_user_id,
                            max_messages=10
                        )

                        # Сгенерировать ответ через Gemini
                        response = await gemini_service.generate_response(
                            query=user_message,
                            user_name="Friend",  # Вставить реальное имя
                            user_context=conversation_context,
                            user_profile={}
                        )

                        # Сохранить ответ аватара
                        await profile_service.save_conversation_turn(
                            user_id=current_user_id,
                            role="assistant",
                            content=response,
                            emotion=None
                        )

                        await db.commit()

                        # Отправить ответ
                        await websocket.send_json({
                            "type": "message_response",
                            "status": "success",
                            "response": response,
                            "emotion": emotion
                        })

                except Exception as e:
                    logger.error(f"❌ WebSocket message ошибка: {e}")
                    await websocket.send_json({"error": str(e)})

    except Exception as e:
        logger.error(f"❌ WebSocket ошибка: {e}")
    finally:
        await websocket.close()
        logger.info("📡 WebSocket клиент отключен")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
