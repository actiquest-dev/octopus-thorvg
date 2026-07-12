"""
Face Detection & Recognition Module
Использует OpenCV Haar Cascade для детектирования лиц и получения embeddings
"""

import asyncio
import base64
import uuid
from typing import List, Optional, Dict, Tuple
import numpy as np
import cv2
from io import BytesIO
from PIL import Image
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Отдельный лог-файл для детектора
_detector_log_file = "/Users/miguelaprossine/octopus-thorvg/backend/detector.log"

def _log_detector(msg: str):
    """Написать в отдельный лог детектора"""
    try:
        with open(_detector_log_file, "a") as f:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

# Load OpenCV Haar Cascade for face detection
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path)

class FaceDetector:
    """
    Детектор лиц с использованием OpenCV Haar Cascade
    Возвращает bounding boxes и базовые атрибуты лиц
    """

    def __init__(self):
        """Инициализировать OpenCV Face Detection"""
        self.face_cascade = face_cascade
        self.initialized = self.face_cascade is not None and not self.face_cascade.empty()

        if self.initialized:
            logger.info("✅ FaceDetector инициализирован с OpenCV")
        else:
            logger.warning("❌ FaceDetector НЕ инициализирован (OpenCV cascade missing)")

    async def detect_faces_from_base64(self, image_b64: str) -> List[Dict]:
        """
        Детектировать лица из JPEG base64 изображения
        """
        print(f"📍 detect_faces_from_base64 START, b64_len={len(image_b64)}", flush=True)

        if not self.initialized:
            print(f"❌ FaceDetector not initialized", flush=True)
            return []

        try:
            print(f"📍 Decoding base64...", flush=True)
            # Декодировать base64 в numpy array
            image_data = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_data))

            # Конвертировать в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')

            image_np = np.array(image)
            height, width, _ = image_np.shape
            print(f"📍 Image loaded: {width}x{height}", flush=True)

            # Запустить в отдельном потоке чтобы не блокировать
            print(f"📍 Calling _detect_faces_sync in executor...", flush=True)
            loop = asyncio.get_event_loop()
            faces = await loop.run_in_executor(
                None,
                self._detect_faces_sync,
                image_np
            )
            print(f"📍 Executor returned {len(faces)} faces", flush=True)

            return faces

        except Exception as e:
            print(f"❌ Error in detect_faces_from_base64: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return []

    def _detect_faces_sync(self, image_np: np.ndarray) -> List[Dict]:
        """Синхронная обработка (запускается в отдельном потоке)"""
        faces = []
        height, width = image_np.shape[:2]

        if not self.initialized:
            print(f"❌ Cascade not initialized", flush=True)
            return faces

        print(f"🔎 Processing {width}x{height} image", flush=True)

        # Конвертировать в grayscale для Haar Cascade
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        print(f"⚫ Converted to grayscale", flush=True)

        # Детектировать лица
        detected_faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        print(f"📊 Haar Cascade found {len(detected_faces)} faces: {detected_faces.tolist() if len(detected_faces) > 0 else '[]'}", flush=True)

        if len(detected_faces) == 0:
            print(f"⚠️ No faces detected", flush=True)
            return faces

        for idx, (x, y, w, h) in enumerate(detected_faces):
            face_id = str(uuid.uuid4())

            # Нормализовать coordinates
            x_min = x / width
            y_min = y / height
            x_max = (x + w) / width
            y_max = (y + h) / height

            bbox = [x_min, y_min, x_max, y_max]

            # Простые keypoints из bounding box
            keypoints = {
                "left_eye": [(x_min + 0.15), (y_min + 0.35)],
                "right_eye": [(x_max - 0.15), (y_min + 0.35)],
                "nose": [(x_min + x_max) / 2, (y_min + 0.5)],
                "mouth_left": [(x_min + 0.3), (y_max - 0.15)],
                "mouth_right": [(x_max - 0.3), (y_max - 0.15)],
            }

            face_info = {
                "face_id": face_id,
                "bbox": bbox,
                "confidence": 0.8,  # Haar Cascade doesn't return confidence
                "landmarks": [],  # Will be empty for Haar Cascade
                "keypoints": keypoints,
                "image_dims": (width, height),
                "embedding": []  # Will be filled later
            }

            faces.append(face_info)
            _log_detector(f"  Face {idx+1}: bbox={bbox}, id={face_id}")

        _log_detector(f"✅ _detect_faces_sync returning {len(faces)} faces")
        return faces


    async def get_face_embeddings(self, faces: List[Dict], image_b64: str) -> List[Dict]:
        """
        Получить простые embeddings на основе геометрии лица
        """
        print(f"🟢 get_face_embeddings called for {len(faces)} faces", flush=True)

        try:
            image_data = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_data))
            image_np = np.array(image)
            height, width, _ = image_np.shape
            print(f"🟢 Image loaded in get_face_embeddings: {width}x{height}", flush=True)

            for idx, face in enumerate(faces):
                print(f"🟢 Processing face {idx} for embedding...", flush=True)
                # Создать простой embedding на основе геометрии
                embedding = self._compute_geometric_embedding(face, image_np)
                face["embedding"] = embedding
                face["embedding_dim"] = len(embedding)
                print(f"🟢   Face {idx}: embedding dim={len(embedding)}", flush=True)

            print(f"🟢 get_face_embeddings DONE, returning {len(faces)} faces", flush=True)
            return faces

        except Exception as e:
            print(f"❌ Error in get_face_embeddings: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return faces

    def _compute_geometric_embedding(self, face: Dict, image: np.ndarray) -> List[float]:
        """
        Вычислить простой embedding на основе геометрии лица
        """
        bbox = face["bbox"]
        keypoints = face["keypoints"]

        print(f"🟢 _compute_geometric_embedding: bbox={bbox}, keypoints={list(keypoints.keys())}", flush=True)

        # Нормализованные координаты
        embedding = [
            bbox[0], bbox[1], bbox[2], bbox[3],  # bbox coordinates (4)
        ]

        # Добавить расстояния между ключевыми точками
        if "left_eye" in keypoints and "right_eye" in keypoints:
            left_eye = keypoints["left_eye"]
            right_eye = keypoints["right_eye"]
            eye_distance = np.sqrt((left_eye[0] - right_eye[0])**2 + (left_eye[1] - right_eye[1])**2)
            embedding.append(eye_distance)

        if "nose" in keypoints:
            nose = keypoints["nose"]
            embedding.extend([nose[0], nose[1]])  # (2)

        if "mouth_left" in keypoints and "mouth_right" in keypoints:
            mouth_left = keypoints["mouth_left"]
            mouth_right = keypoints["mouth_right"]
            mouth_width = np.sqrt((mouth_left[0] - mouth_right[0])**2 + (mouth_left[1] - mouth_right[1])**2)
            embedding.append(mouth_width)

        # Добавить ещё базовые признаки для расширения embedding
        while len(embedding) < 128:
            embedding.append(0.0)

        print(f"🟢 _compute_geometric_embedding: computed embedding len={len(embedding)}", flush=True)
        return embedding[:128]  # Нормализовать до 128 dimensions

    def extract_face_crop(self, image_b64: str, face: Dict, expand: float = 0.2) -> Optional[str]:
        """
        Извлечь область лица из изображения

        Args:
            image_b64: JPEG в base64
            face: информация о лице с bbox
            expand: расширение bbox (относительно размера)

        Returns:
            Обрезанное лицо в base64 или None
        """
        try:
            image_data = base64.b64decode(image_b64)
            image = Image.open(BytesIO(image_data))
            image_np = np.array(image)
            height, width, _ = image_np.shape

            bbox = face["bbox"]
            x1, y1, x2, y2 = bbox

            # Конвертировать нормализованные координаты в пиксели
            x1 = int(x1 * width)
            y1 = int(y1 * height)
            x2 = int(x2 * width)
            y2 = int(y2 * height)

            # Расширить bbox
            face_width = x2 - x1
            face_height = y2 - y1
            expand_px_x = int(face_width * expand)
            expand_px_y = int(face_height * expand)

            x1 = max(0, x1 - expand_px_x)
            y1 = max(0, y1 - expand_px_y)
            x2 = min(width, x2 + expand_px_x)
            y2 = min(height, y2 + expand_px_y)

            # Обрезать
            face_crop = image_np[y1:y2, x1:x2]

            # Сохранить в base64
            face_pil = Image.fromarray(face_crop)
            buffer = BytesIO()
            face_pil.save(buffer, format="JPEG", quality=90)
            face_b64 = base64.b64encode(buffer.getvalue()).decode()

            return face_b64

        except Exception as e:
            logger.error(f"❌ Ошибка при обрезке лица: {e}")
            return None

    def __del__(self):
        """Очистить ресурсы"""
        pass  # OpenCV doesn't need explicit cleanup


# Глобальный экземпляр детектора
_face_detector: Optional[FaceDetector] = None


def get_face_detector() -> FaceDetector:
    """Получить глобальный экземпляр face detector"""
    global _face_detector
    if _face_detector is None:
        _face_detector = FaceDetector()
    return _face_detector


async def detect_and_process_faces(image_b64: str) -> List[Dict]:
    """
    Полная обработка изображения: детектирование + embeddings
    """
    print(f"🟢 detect_and_process_faces START", flush=True)
    detector = get_face_detector()

    # Шаг 1: Детектировать лица
    print(f"🟢 Step 1: Detecting faces...", flush=True)
    faces = await detector.detect_faces_from_base64(image_b64)
    print(f"🟢 Step 1 result: {len(faces)} faces", flush=True)

    if not faces:
        print(f"🟢 No faces, returning empty", flush=True)
        return []

    # Шаг 2: Получить embeddings
    print(f"🟢 Step 2: Getting embeddings...", flush=True)
    faces = await detector.get_face_embeddings(faces, image_b64)
    print(f"🟢 Step 2 result: {len(faces)} faces with embeddings", flush=True)

    for i, face in enumerate(faces):
        print(f"🟢   Face {i}: embedding_len={len(face.get('embedding', []))}", flush=True)

    # Шаг 3: Извлечь обрезанные области лиц
    print(f"🟢 Step 3: Extracting face crops...", flush=True)
    for face in faces:
        face_crop = detector.extract_face_crop(image_b64, face)
        if face_crop:
            face["face_crop_b64"] = face_crop

    print(f"🟢 detect_and_process_faces DONE, returning {len(faces)} faces", flush=True)
    return faces
