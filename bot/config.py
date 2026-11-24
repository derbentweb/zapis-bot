import os
from pathlib import Path

from dotenv import load_dotenv

# Читаем .env из корня проекта, независимо от того, где запущен терминал.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(part.strip())
    for part in os.getenv("ADMIN_IDS", "").split(",")
    if part.strip().isdigit()
}


def _system_proxy() -> str | None:
    """Прокси из настроек Windows — его же использует браузер."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            if winreg.QueryValueEx(key, "ProxyEnable")[0]:
                return winreg.QueryValueEx(key, "ProxyServer")[0].strip()
    except (OSError, ImportError):
        pass
    return None


PROXY = os.getenv("PROXY", "").strip() or _system_proxy()
if PROXY and "://" not in PROXY:
    PROXY = f"http://{PROXY}"

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError(
        "Нет токена. Скопируй .env.example в .env и вставь токен от @BotFather."
    )
