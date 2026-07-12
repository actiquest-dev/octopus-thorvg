"""
Face Recognition Service
Распознавание лиц, получение embeddings, сравнение лиц
"""

import face_recognition
import cv2
import numpy as np
from typing import Optional, List, Tuple
from PIL import Image
import io
import hashlib
from loguru import logger


class FaceRecognitionService:
    """Сервис распознавания лиц"""

    # Константы
    EMBEDDING_DIM = 128  # Размерность embedding вектора
    DISTANCE_THRESHOLD = 0.6  # Порог для идентификации лица (чем ниже, тем строже)

    def __init__(self):
        """Инициализировать сервис"""
        self.model = "hog"  # или "cnn" для более точного, но медленнее
        logger.info("✅ FaceRecognitionService инициализирован")

    def extract_face_embedding(
        self,
        image_data: bytes,
        quality_threshold: float = 0.5
    ) -> Optional[Tuple[List[float], float, str]]:
        """
        Извлечь embedding лица из изображения

        Args:
            image_data: Бинарные данные изображения
            quality_threshold: Минимальный порог качества (0-1)

        Returns:
            (embedding: List[float], quality_score: float, image_hash: str) или None
        """
        try:
            # Загрузить изображение
            image = face_recognition.load_image_file(io.BytesIO(image_data))

            # Найти все лица в изображении
            face_locations = face_recognition.face_locations(image, model=self.model)

            if not face_locations:
                logger.warning("❌ Лица не найдены в изображении")
                return None

            # Берём первое лицо (если несколько)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if not face_encodings:
                logger.warning("❌ Encoding лица не получен")
                return None

            embedding = face_encodings[0].tolist()  # Конвертировать в список

            # Оценить качество лица (основано на размере лица)
            top, right, bottom, left = face_locations[0]
            face_area = (right - left) * (bottom - top)
            image_area = image.shape[0] * image.shape[1]
            quality_score = min(1.0, face_area / (image_area * 0.1))  # Примерный алгоритм

            if quality_score < quality_threshold:
                logger.warning(f"⚠️ Качество лица низкое: {quality_score:.2f}")
                return None

            # Создать хэш изображения
            image_hash = hashlib.sha256(image_data).hexdigest()

            logger.info(f"✅ Embedding извлечён, качество: {quality_score:.2f}")
            return embedding, quality_score, image_hash

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения embedding: {e}")
            return None

    def compare_faces(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> Tuple[bool, float]:
        """
        Сравнить два embeddings лиц

        Args:
            embedding1: Первый embedding
            embedding2: Второй embedding

        Returns:
            (is_same_person: bool, distance: float)
        """
        try:
            embedding1 = np.array(embedding1)
            embedding2 = np.array(embedding2)

            # Euclidean distance между embeddings
            distance = np.linalg.norm(embedding1 - embedding2)

            is_same = distance < self.DISTANCE_THRESHOLD

            logger.info(f"📊 Сравнение лиц: расстояние={distance:.4f}, совпадение={is_same}")
            return is_same, distance

        except Exception as e:
            logger.error(f"❌ Ошибка сравнения лиц: {e}")
            return False, 1.0

    def find_best_match(
        self,
        embedding: List[float],
        stored_embeddings: List[Tuple[str, List[float]]]
    ) -> Optional[Tuple[str, float]]:
        """
        Найти лучшее совпадение среди сохранённых embeddings

        Args:
            embedding: Embedding для поиска
            stored_embeddings: Список (user_id, embedding) пар

        Returns:
            (user_id, distance) или None
        """
        if not stored_embeddings:
            return None

        try:
            embedding = np.array(embedding)
            best_match = None
            best_distance = self.DISTANCE_THRESHOLD

            for user_id, stored_emb in stored_embeddings:
                stored_emb = np.array(stored_emb)
                distance = np.linalg.norm(embedding - stored_emb)

                if distance < best_distance:
                    best_distance = distance
                    best_match = (user_id, distance)

            if best_match:
                logger.info(f"🎯 Найдено совпадение: user_id={best_match[0]}, расстояние={best_match[1]:.4f}")

            return best_match

        except Exception as e:
            logger.error(f"❌ Ошибка поиска совпадения: {e}")
            return None

    def extract_face_from_image(
        self,
        image_data: bytes,
        face_index: int = 0
    ) -> Optional[bytes]:
        """
        Извлечь лицо из изображения и вернуть его отдельно

        Args:
            image_data: Бинарные данные исходного изображения
            face_index: Индекс лица (если несколько)

        Returns:
            Бинарные данные обрезанного изображения или None
        """
        try:
            # Загрузить изображение
            image = face_recognition.load_image_file(io.BytesIO(image_data))
            face_locations = face_recognition.face_locations(image, model=self.model)

            if not face_locations or face_index >= len(face_locations):
                logger.warning("❌ Лица не найдены или индекс неверный")
                return None

            top, right, bottom, left = face_locations[face_index]

            # Добавить margin вокруг лица
            margin = 20
            top = max(0, top - margin)
            left = max(0, left - margin)
            bottom = min(image.shape[0], bottom + margin)
            right = min(image.shape[1], right + margin)

            # Обрезать лицо
            face_image = image[top:bottom, left:right]

            # Конвертировать обратно в RGB (OpenCV использует BGR)
            face_image_rgb = cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR)

            # Сохранить в bytes
            success, buffer = cv2.imencode('.jpg', face_image_rgb)
            if success:
                face_bytes = buffer.tobytes()
                logger.info(f"✅ Лицо извлечено, размер: {len(face_bytes)} байт")
                return face_bytes

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения лица: {e}")
            return None

    def batch_process_embeddings(
        self,
        image_data_list: List[bytes]
    ) -> List[Optional[Tuple[List[float], float, str]]]:
        """
        Обработать несколько изображений и получить embeddings

        Args:
            image_data_list: Список бинарных данных изображений

        Returns:
            Список результатов
        """
        results = []
        for image_data in image_data_list:
            result = self.extract_face_embedding(image_data)
            results.append(result)
        return results

    @staticmethod
    def get_embedding_vector_size() -> int:
        """Получить размерность embedding вектора"""
        return FaceRecognitionService.EMBEDDING_DIM

    @staticmethod
    def get_distance_threshold() -> float:
        """Получить порог расстояния"""
        return FaceRecognitionService.DISTANCE_THRESHOLD

    def tune_distance_threshold(self, new_threshold: float):
        """Изменить порог расстояния (0.4 = строго, 0.8 = мягче)"""
        self.DISTANCE_THRESHOLD = new_threshold
        logger.info(f"⚙️ Порог расстояния изменен на {new_threshold}")
