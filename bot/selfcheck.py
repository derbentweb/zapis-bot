"""Быстрая проверка без Telegram: зависимости, .env, запись/чтение заявок."""
import asyncio
import tempfile
from pathlib import Path

from config import BOT_TOKEN, ADMIN_IDS
import storage


async def main() -> None:
    assert BOT_TOKEN and ":" in BOT_TOKEN, "нет токена в .env"
    assert ADMIN_IDS, "нет ADMIN_IDS в .env"

    original = storage.DB_PATH
    with tempfile.TemporaryDirectory() as tmp:
        storage.DB_PATH = Path(tmp) / "bookings.json"
        first = await storage.add_booking({"name": "Тест", "phone": "+7000"})
        second = await storage.add_booking({"name": "Тест 2", "phone": "+7001"})
        assert (first, second) == (1, 2), (first, second)
        assert len(storage.list_bookings()) == 2
        assert storage.list_bookings()[0]["name"] == "Тест"
    storage.DB_PATH = original
    print("OK: токен, админы и хранилище в порядке.")


if __name__ == "__main__":
    asyncio.run(main())
