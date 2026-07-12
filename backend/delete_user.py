#!/usr/bin/env python3
"""
Скрипт для удаления пользователя из базы по имени или ID
"""
import asyncio
import sys
from face_db_postgres import get_face_database

async def list_users():
    """Показать всех пользователей в базе"""
    db = await get_face_database()
    users = await db.get_all_users()

    if not users:
        print("❌ В базе нет пользователей")
        return

    print("\n📋 Пользователи в базе:")
    print("─" * 60)
    for user in users:
        print(f"  ID: {user['user_id']}")
        print(f"  Имя: {user['name']}")
        print(f"  Лиц: {user['face_count']}")
        print(f"  Создан: {user['created_at']}")
        print("─" * 60)

async def delete_user_by_name(name: str):
    """Удалить пользователя по имени"""
    db = await get_face_database()

    # Найти пользователя по имени
    from sqlalchemy import text
    from face_db_postgres import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id FROM users WHERE LOWER(name) = LOWER(:name)"), {"name": name})
        user_id = result.scalar()

    if not user_id:
        print(f"❌ Пользователь '{name}' не найден")
        return False

    # Удалить пользователя
    success = await db.delete_user(user_id)
    if success:
        print(f"✅ Пользователь '{name}' удалён из базы")
    else:
        print(f"❌ Ошибка при удалении '{name}'")

    return success

async def delete_user_by_id(user_id: str):
    """Удалить пользователя по ID"""
    db = await get_face_database()
    success = await db.delete_user(user_id)

    if success:
        print(f"✅ Пользователь с ID {user_id} удалён")
    else:
        print(f"❌ Пользователь с ID {user_id} не найден")

    return success

async def main():
    if len(sys.argv) == 1:
        # Показать всех пользователей
        await list_users()
    elif len(sys.argv) == 3 and sys.argv[1] == "--name":
        # Удалить по имени
        await delete_user_by_name(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "--id":
        # Удалить по ID
        await delete_user_by_id(sys.argv[2])
    else:
        print("Usage:")
        print("  python delete_user.py                 # Show all users")
        print("  python delete_user.py --name 'Миша'   # Delete user by name")
        print("  python delete_user.py --id 'UUID'     # Delete user by ID")

if __name__ == "__main__":
    asyncio.run(main())
