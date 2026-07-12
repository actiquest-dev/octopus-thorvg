"""
SQLAlchemy модели для PostgreSQL
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, ForeignKey, Text, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Профиль
    profile_data = Column(JSON, nullable=True)
    bio = Column(Text, nullable=True)

    # Face ID
    face_profiles = relationship("FaceProfile", back_populates="user", cascade="all, delete-orphan")

    # Статистика
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    interaction_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "profile_data": self.profile_data,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "interaction_count": self.interaction_count,
        }


class FaceProfile(Base):
    """Профиль лица пользователя"""
    __tablename__ = "face_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="face_profiles")

    # Embedding (вектор лица) - используем JSON для хранения массива чисел
    embedding = Column(JSON, nullable=False)  # List[float] 128-dim

    # Изображение (опционально - можно хранить путь в S3/MinIO)
    image_data = Column(LargeBinary, nullable=True)  # Если нужно хранить в БД
    image_hash = Column(String(64), unique=True, nullable=True, index=True)

    # Метаданные
    quality_score = Column(Float, default=0.0)  # 0-1
    confidence = Column(Float, default=0.0)  # 0-1 confidence of detection

    # Временные метки
    captured_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConversationHistory(Base):
    """История разговора пользователя (для RAG контекста в Gemini)"""
    __tablename__ = "conversation_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Сообщение
    role = Column(String(20), nullable=False)  # "user" или "assistant"
    content = Column(Text, nullable=False)

    # Эмоции и контекст
    emotion = Column(String(50), nullable=True)  # happy, sad, angry, etc.
    context_tags = Column(JSON, nullable=True)  # Теги контекста для RAG

    # Вложения
    embedding = Column(JSON, nullable=True)  # Embedding сообщения для поиска

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "emotion": self.emotion,
            "context_tags": self.context_tags,
            "created_at": self.created_at.isoformat(),
        }


class UserAction(Base):
    """Логирование действий пользователя"""
    __tablename__ = "user_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    action_type = Column(String(50), nullable=False)  # "login", "query", "action", etc
    description = Column(Text, nullable=True)

    # Результат
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Метаданные
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "description": self.description,
            "success": self.success,
            "created_at": self.created_at.isoformat(),
        }


class RAGDocument(Base):
    """Документы для RAG контекста (база знаний)"""
    __tablename__ = "rag_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Содержимое
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Embedding для поиска
    embedding = Column(JSON, nullable=False)  # Embedding контента

    # Метаданные
    source = Column(String(255), nullable=True)  # Откуда документ
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, nullable=True)

    # Управление
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }
