import asyncio
import json
from pathlib import Path

DB_PATH = Path(__file__).with_name("bookings.json")
_lock = asyncio.Lock()


def _read() -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        data = json.loads(DB_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


async def add_booking(booking: dict) -> int:
    """Add a booking, return its id. Locked so parallel writes can't corrupt the file."""
    async with _lock:
        items = _read()
        booking_id = max((item.get("id", 0) for item in items), default=0) + 1
        booking["id"] = booking_id
        items.append(booking)
        DB_PATH.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return booking_id


def list_bookings() -> list[dict]:
    return _read()
