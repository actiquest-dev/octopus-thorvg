"""
Пример использования Face Recognition API
"""

import asyncio
import aiohttp
import json
from pathlib import Path

API_BASE = "http://localhost:8000"


async def example_full_workflow():
    """Полный workflow: регистрация -> лицо -> идентификация -> Gemini"""

    async with aiohttp.ClientSession() as session:
        print("🚀 Запуск примера Face Recognition API\n")

        # === 1. Регистрация пользователя ===
        print("1️⃣ Регистрация пользователя")
        print("-" * 50)

        user_data = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "phone": "+1234567890"
        }

        async with session.post(
            f"{API_BASE}/api/users/register",
            json=user_data
        ) as resp:
            user = await resp.json()
            user_id = user["id"]
            print(f"✅ Пользователь создан:")
            print(json.dumps(user, indent=2))
            print(f"\nUser ID: {user_id}\n")

        # === 2. Регистрация лица ===
        print("2️⃣ Регистрация лица пользователя")
        print("-" * 50)

        # Используем пример изображения (нужно создать или загрузить)
        face_image_path = Path("example_face.jpg")

        if face_image_path.exists():
            with open(face_image_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='face.jpg')

                async with session.post(
                    f"{API_BASE}/api/faces/register/{user_id}",
                    data=data
                ) as resp:
                    face_profile = await resp.json()
                    print(f"✅ Лицо зарегистрировано:")
                    print(json.dumps(face_profile, indent=2))
                    print()
        else:
            print(f"⚠️ Файл {face_image_path} не найден")
            print("Используйте реальное изображение для тестирования\n")

        # === 3. Получить информацию о пользователе ===
        print("3️⃣ Получить информацию о пользователе")
        print("-" * 50)

        async with session.get(f"{API_BASE}/api/users/{user_id}") as resp:
            user_info = await resp.json()
            print(f"✅ Информация о пользователе:")
            print(json.dumps(user_info, indent=2))
            print()

        # === 4. Идентифицировать лицо ===
        print("4️⃣ Идентифицировать лицо")
        print("-" * 50)

        if face_image_path.exists():
            with open(face_image_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='face.jpg')

                async with session.post(
                    f"{API_BASE}/api/faces/identify",
                    data=data
                ) as resp:
                    if resp.status == 200:
                        identified = await resp.json()
                        print(f"✅ Лицо идентифицировано:")
                        print(json.dumps(identified, indent=2))
                        print()
                    else:
                        error = await resp.json()
                        print(f"❌ Ошибка идентификации: {error}\n")
        else:
            print("⚠️ Используйте изображение для тестирования\n")

        # === 5. Запрос к Gemini ===
        print("5️⃣ Запрос к Gemini с контекстом")
        print("-" * 50)

        query_data = {
            "user_id": user_id,
            "query": "Tell me about my profile based on what you know",
            "use_rag": True
        }

        async with session.post(
            f"{API_BASE}/api/gemini/query",
            json=query_data
        ) as resp:
            if resp.status == 200:
                gemini_response = await resp.json()
                print(f"✅ Ответ от Gemini:")
                print(f"Query: {gemini_response['query']}")
                print(f"Response: {gemini_response['response']}")
                print(f"Context docs used: {gemini_response['context_docs']}\n")
            else:
                error = await resp.json()
                print(f"⚠️ Ошибка Gemini: {error}\n")

        print("=" * 50)
        print("✅ Пример завершён успешно!")


async def example_multiple_faces():
    """Пример: Регистрация нескольких лиц для одного пользователя"""

    async with aiohttp.ClientSession() as session:
        print("\n🎭 Пример: Несколько лиц для одного пользователя")
        print("=" * 50)

        # Создать пользователя
        user_data = {
            "name": "Bob Smith",
            "email": "bob@example.com"
        }

        async with session.post(
            f"{API_BASE}/api/users/register",
            json=user_data
        ) as resp:
            user = await resp.json()
            user_id = user["id"]
            print(f"✅ Пользователь: {user['name']} (ID: {user_id})")

        # Регистрировать несколько лиц
        face_files = ["face1.jpg", "face2.jpg", "face3.jpg"]

        for i, face_file in enumerate(face_files, 1):
            face_path = Path(face_file)
            if face_path.exists():
                print(f"\n📸 Загрузка лица {i}")

                with open(face_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=face_file)

                    async with session.post(
                        f"{API_BASE}/api/faces/register/{user_id}",
                        data=data
                    ) as resp:
                        face_profile = await resp.json()
                        print(f"✅ Лицо {i}: качество={face_profile.get('quality_score', 0):.2f}")
            else:
                print(f"⚠️ Файл {face_file} не найден")


async def example_batch_identification():
    """Пример: Массовая идентификация нескольких лиц"""

    async with aiohttp.ClientSession() as session:
        print("\n👥 Пример: Массовая идентификация")
        print("=" * 50)

        test_images = ["test1.jpg", "test2.jpg", "test3.jpg"]

        for image_file in test_images:
            image_path = Path(image_file)
            if image_path.exists():
                print(f"\n🔍 Идентифицирую: {image_file}")

                with open(image_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=image_file)

                    async with session.post(
                        f"{API_BASE}/api/faces/identify",
                        data=data
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            print(f"✅ Найдено: {result['name']} (confidence: {result['confidence']:.2f})")
                        else:
                            print(f"❌ Не идентифицировано")
            else:
                print(f"⚠️ Файл {image_file} не найден")


def check_api_health():
    """Проверить здоровье API"""
    import requests

    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ API работает")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"❌ API вернул статус {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ API недоступен на {API_BASE}")
        print("Убедитесь, что запущен: python -m uvicorn main:app --reload")


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("🎯 Face Recognition API - Примеры использования")
    print("=" * 60)

    # Сначала проверить здоровье API
    check_api_health()
    print()

    # Запустить примеры
    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == "full":
            asyncio.run(example_full_workflow())
        elif example == "multiple":
            asyncio.run(example_multiple_faces())
        elif example == "batch":
            asyncio.run(example_batch_identification())
        else:
            print(f"Unknown example: {example}")
            print("Available: full, multiple, batch")
    else:
        # По умолчанию запустить полный workflow
        print("\nЗапуск полного workflow...")
        print("(Используйте 'python example_usage.py full/multiple/batch')\n")
        asyncio.run(example_full_workflow())
