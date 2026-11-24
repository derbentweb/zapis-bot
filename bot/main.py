import asyncio
import os
import traceback
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

from config import ADMIN_IDS, BOT_TOKEN, PROXY
import storage

# НАСТРОЙКА ПОД КЛИЕНТА: услуги, часы и название салона.
SALON = "СТУДИЯ КРАСОТЫ"
SERVICES = {
    "haircut": "💇 Стрижка",
    "coloring": "🎨 Окрашивание",
    "manicure": "💅 Маникюр",
    "pedicure": "🦶 Педикюр",
    "brows": "✨ Брови",
    "massage": "💆 Массаж",
}
SLOTS = ["10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00"]
BANNER = Path(__file__).resolve().parent.parent / "assets" / "banner.png"

BTN_BOOK = "📝 Записаться"
BTN_HELP = "ℹ️ Как записаться"
BTN_LIST = "📋 Мои заявки"
BTN_CANCEL = "❌ Отмена"
BTN_CONTACT = "📱 Отправить номер"

STEPS = (
    "1️⃣ Выберите услугу\n"
    "2️⃣ Укажите удобное время\n"
    "3️⃣ Оставьте имя и номер — готово"
)


class Booking(StatesGroup):
    choosing_time = State()
    name = State()
    phone = State()


session = AiohttpSession(proxy=PROXY) if PROXY else AiohttpSession()
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())


def services_keyboard():
    kb = InlineKeyboardBuilder()
    for key, title in SERVICES.items():
        kb.button(text=title, callback_data=f"srv:{key}")
    kb.button(text=BTN_CANCEL, callback_data="cancel")
    kb.adjust(2)
    return kb.as_markup()


def time_keyboard():
    kb = InlineKeyboardBuilder()
    for slot in SLOTS:
        kb.button(text=f"🕒 {slot}", callback_data=f"time:{slot}")
    kb.button(text=BTN_CANCEL, callback_data="cancel")
    kb.adjust(3)
    return kb.as_markup()


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOOK)],
            [KeyboardButton(text=BTN_HELP), KeyboardButton(text=BTN_LIST)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONTACT, request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def instructions() -> str:
    return (
        f"{SALON}\n\n"
        "Добро пожаловать! Запись занимает 30 секунд.\n\n"
        "Как записаться:\n"
        f"{STEPS}\n\n"
        "Нажмите «Записаться» 👇"
    )


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer_photo(
        photo=FSInputFile(BANNER),
        caption=instructions(),
        reply_markup=main_menu(),
    )


@dp.message(Command("help"))
@dp.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(instructions(), reply_markup=main_menu())


@dp.message(Command("cancel"))
@dp.message(F.text == BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Запись отменена. Нажмите «Записаться», чтобы начать заново.", reply_markup=main_menu())


@dp.message(Command("bookings"))
@dp.message(F.text == BTN_LIST)
async def cmd_bookings(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Список заявок доступен только администратору.", reply_markup=main_menu())
        return
    items = storage.list_bookings()
    if not items:
        await message.answer("Заявок пока нет.", reply_markup=main_menu())
        return
    header = f"📋 Всего заявок: {len(items)}. Последние 10:\n\n"
    rows = [
        f"#{b['id']} · {b['service']} · {b['time']}\n{b['name']} · {b['phone']}"
        for b in items[-10:]
    ]
    await message.answer(header + "\n\n".join(rows), reply_markup=main_menu())


@dp.message(F.text == BTN_BOOK)
async def menu_book(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Шаг 1 из 3 · Услуга\n\nВыберите услугу из списка 👇",
        reply_markup=services_keyboard(),
    )


@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Запись отменена. Нажмите «Записаться», чтобы начать заново.")
    await callback.answer()


@dp.callback_query(F.data.startswith("srv:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    service = SERVICES.get(key, key)
    await state.update_data(service=service)
    await state.set_state(Booking.choosing_time)
    await callback.message.edit_text(
        f"Шаг 2 из 3 · Время\n\nВыбрано: {service}\n\nТеперь выберите удобное время 👇",
        reply_markup=time_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext) -> None:
    slot = callback.data.split(":", 1)[1]
    await state.update_data(time=slot)
    await state.set_state(Booking.name)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Шаг 3 из 3 · Контакты\n\nВыбрано: {data['service']} · {slot}\n\n"
        "Напишите, как к вам обращаться 👇"
    )
    await callback.answer()


@dp.message(Booking.name)
async def get_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Напишите имя текстом 👇")
        return
    await state.update_data(name=name)
    await state.set_state(Booking.phone)
    await message.answer(
        f"Шаг 3 из 3 · Контакты\n\nИмя: {name}\n\n"
        "Нажмите «Отправить номер» — это быстрее, чем печатать 👇",
        reply_markup=contact_keyboard(),
    )


@dp.message(Booking.phone)
async def get_phone(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not phone:
        await message.answer("Нажмите «Отправить номер» или введите номер 👇", reply_markup=contact_keyboard())
        return

    data = await state.get_data()
    await state.clear()

    booking = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "service": data.get("service"),
        "time": data.get("time"),
        "name": data.get("name"),
        "phone": phone,
    }
    booking_id = await storage.add_booking(booking)

    await message.answer(
        f"✅ Заявка №{booking_id} принята\n\n"
        f"Услуга: {booking['service']}\n"
        f"Время: {booking['time']}\n"
        f"Имя: {booking['name']}\n"
        f"Телефон: {phone}\n\n"
        "Мы свяжемся с вами для подтверждения.\n\n"
        "Хотите записаться ещё раз? Нажмите «Записаться» 👇",
        reply_markup=main_menu(),
    )

    alert = (
        f"🔔 Новая заявка №{booking_id}\n\n"
        f"{booking['service']} · {booking['time']}\n"
        f"{booking['name']} · {phone}\n"
        f"@{booking['username'] or 'без ника'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, alert)
        except Exception as exc:
            print(f"Не удалось уведомить админа {admin_id}: {exc}")


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer("Нажмите «Записаться» в меню 👇", reply_markup=main_menu())


async def health_server() -> None:
    """HTTP-сервер, чтобы облако видело, что сервис живой."""
    app = web.Application()

    async def ping(request):
        return web.Response(text="OK")

    app.router.add_get("/", ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
    await site.start()


async def main() -> None:
    try:
        me = await bot.get_me()
    except Exception as exc:
        raise RuntimeError(
            f"Не удалось подключиться к Telegram: {exc}\n"
            "Проверь BOT_TOKEN в .env и интернет."
        ) from exc

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="help", description="Как записаться"),
            BotCommand(command="cancel", description="Отменить запись"),
            BotCommand(command="bookings", description="Заявки (админ)"),
        ]
    )

    print(f"Подключено: @{me.username} ({me.full_name})")
    print(f"Админы: {sorted(ADMIN_IDS)}")
    print(f"Прокси: {PROXY or 'нет (прямое подключение)'}")
    print("Бот запущен. НЕ ЗАКРЫВАЙ это окно. Ctrl+C — остановить.")
    await health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        text = traceback.format_exc()
        log = Path(__file__).resolve().parent.parent / "error.log"
        log.write_text(text, encoding="utf-8")
        print(text)
        print(f"Ошибка записана в {log.name} — пришли мне этот файл.")
        input("Нажми Enter, чтобы закрыть окно...")
