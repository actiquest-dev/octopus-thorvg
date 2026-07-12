"""
Face ID REST API Endpoints
Управление регистрацией, идентификацией и профилями пользователей
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from pydantic import BaseModel
import base64
import io
from PIL import Image
import numpy as np
from loguru import logger
from typing import Optional, List

from face_detector import FaceDetector
from face_db_postgres import get_face_database


router = APIRouter(prefix="/api/face", tags=["face"])
face_detector = FaceDetector()


class UserRegisterRequest(BaseModel):
    """Request model for user registration"""
    name: str
    image_b64: str  # Base64 encoded JPEG image


class UserRegisterResponse(BaseModel):
    """Response model for user registration"""
    user_id: str
    name: str
    face_profile_id: str
    status: str = "registered"


class FaceIdentifyRequest(BaseModel):
    """Request model for face identification"""
    image_b64: str
    threshold: float = 0.6


class FaceIdentifyResponse(BaseModel):
    """Response model for face identification"""
    matched: bool
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: str


class UserProfile(BaseModel):
    """User profile data"""
    user_id: str
    name: str
    interaction_count: int
    last_seen: str
    created_at: str


@router.post("/register", response_model=UserRegisterResponse)
async def register_user(request: UserRegisterRequest):
    """
    Register a new user with face recognition

    Args:
        name: User name
        image_b64: Base64 encoded JPEG image (face must be clearly visible)

    Returns:
        Registered user data
    """
    try:
        # Decode image
        image_data = base64.b64decode(request.image_b64)
        image = Image.open(io.BytesIO(image_data))

        # Detect faces and get embeddings
        faces = await face_detector.detect_and_embed_from_pil(image)

        if not faces:
            raise HTTPException(status_code=400, detail="No face detected in image")

        # Use the first detected face
        face = faces[0]
        embedding = face["embedding"]

        # Register in database
        db = await get_face_database()
        result = await db.register_new_user(
            name=request.name,
            embedding=embedding,
            profile_data={
                "registration_timestamp": __import__("time").time()
            }
        )

        return UserRegisterResponse(
            user_id=result["user_id"],
            name=result["name"],
            face_profile_id=result["face_profile_id"],
            status="registered"
        )

    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/identify", response_model=FaceIdentifyResponse)
async def identify_face(request: FaceIdentifyRequest):
    """
    Identify user from face image

    Args:
        image_b64: Base64 encoded JPEG image
        threshold: Cosine similarity threshold (0-1, default 0.6)

    Returns:
        Identified user or null if no match
    """
    try:
        import time as time_module

        # Decode image
        image_data = base64.b64decode(request.image_b64)
        image = Image.open(io.BytesIO(image_data))

        # Detect faces and get embeddings
        faces = await face_detector.detect_and_embed_from_pil(image)

        if not faces:
            return FaceIdentifyResponse(
                matched=False,
                timestamp=__import__("datetime").datetime.utcnow().isoformat()
            )

        # Use the first detected face
        face = faces[0]
        embedding = face["embedding"]

        # Search database
        db = await get_face_database()
        user = await db.find_user_by_face(embedding, threshold=request.threshold)

        if user:
            return FaceIdentifyResponse(
                matched=True,
                user_id=user["user_id"],
                user_name=user["name"],
                confidence=user["confidence"],
                timestamp=__import__("datetime").datetime.utcnow().isoformat()
            )
        else:
            return FaceIdentifyResponse(
                matched=False,
                timestamp=__import__("datetime").datetime.utcnow().isoformat()
            )

    except Exception as e:
        logger.error(f"❌ Identification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Get user profile and history"""
    try:
        db = await get_face_database()
        history = await db.get_user_history(user_id)

        if not history:
            raise HTTPException(status_code=404, detail="User not found")

        return UserProfile(
            user_id=history["user_id"],
            name=history["name"],
            interaction_count=history["interaction_count"],
            last_seen=history["last_seen"] or "",
            created_at=history["created_at"] or ""
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_database_stats():
    """Get Face ID database statistics"""
    try:
        db = await get_face_database()
        stats = await db.get_stats()
        return stats

    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/interaction")
async def log_interaction(
    user_id: str,
    emotion: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    message: Optional[str] = Query(None)
):
    """Log user interaction (emotion, action, message)"""
    try:
        db = await get_face_database()
        success = await db.add_interaction(
            user_id=user_id,
            emotion=emotion,
            action=action,
            message=message
        )

        if success:
            return {"status": "logged", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error logging interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}")
async def delete_user(user_id: str):
    """Delete user and all associated data"""
    try:
        db = await get_face_database()
        success = await db.delete_user(user_id)

        if success:
            return {"status": "deleted", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def face_api_info():
    """Face ID API information"""
    db = await get_face_database()
    stats = await db.get_stats()

    return {
        "service": "Face ID Recognition Backend",
        "version": "1.0.0",
        "status": "ready",
        "database_stats": stats,
        "endpoints": {
            "register": "POST /api/face/register",
            "identify": "POST /api/face/identify",
            "user_profile": "GET /api/face/user/{user_id}",
            "log_interaction": "POST /api/face/user/{user_id}/interaction",
            "delete_user": "DELETE /api/face/user/{user_id}",
            "stats": "GET /api/face/stats"
        }
    }
