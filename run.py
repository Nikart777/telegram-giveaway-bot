import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.utils import executor
from dotenv import load_dotenv

# Функция загрузки секретов
def get_secret(name, default=None):
    try:
        secret_path = f"/run/secrets/{name}"
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                return f.read().strip()
        return os.getenv(name, default)
    except Exception as e:
        logging.error(f"Ошибка при загрузке секрета {name}: {e}")
        return default

# Загружаем токен и ID админа
load_dotenv()
BOT_TOKEN = get_secret("BOT_TOKEN")
ADMIN_ID = int(get_secret("ADMIN_ID", 0))

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("❌ BOT_TOKEN или ADMIN_ID не указаны!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# Кнопка "Новая жалоба"
main_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("🆕 Новая жалоба", callback_data="new_complaint")
)

# Выбор клуба
club_menu = InlineKeyboardMarkup(row_width=1)
club_menu.add(
    InlineKeyboardButton("Cyberx Новокосино", callback_data="club_novokosino"),
    InlineKeyboardButton("Cyberx Алтуфьево", callback_data="club_altufevo")
)

# Словарь для хранения данных пользователя
user_data = {}

@dp.message_handler(commands=['start'])
async def start_command(message: Message):
    user_data[message.chat.id] = {}  # Сброс данных
    await message.answer(
        "👋 Добро пожаловать! Выберите клуб, для которого хотите оставить жалобу:",
        reply_markup=club_menu
    )

@dp.callback_query_handler(lambda c: c.data.startswith("club_"))
async def select_club(callback_query: CallbackQuery):
    club = "Новокосино" if callback_query.data == "club_novokosino" else "Алтуфьево"
    user_data[callback_query.message.chat.id]["club"] = club
    await callback_query.message.edit_text(
        f"✅ Вы выбрали клуб Cyberx {club}.\nТеперь вы можете оставить жалобу.",
        reply_markup=main_menu
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "new_complaint")
async def new_complaint(callback_query: CallbackQuery):
    # Обновляем текст сообщения с инструкцией
    await callback_query.message.edit_text(
        "📌 Отправьте вашу жалобу:\n"
        "1️⃣ Номер ПК\n"
        "2️⃣ Описание проблемы\n"
        "3️⃣ Обязательно фото",
        reply_markup=main_menu  # Кнопка остается на месте
    )
    await callback_query.answer()

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: Message):
    if "club" not in user_data.get(message.chat.id, {}):
        await message.reply("❌ Пожалуйста, сначала выберите клуб через /start.")
        return

    if not message.caption:
        await message.reply("❌ Пожалуйста, добавьте описание проблемы вместе с фото.")
        return

    club = user_data[message.chat.id]["club"]

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"🔴 *Новая жалоба*\n\n"
                f"👨‍💻 От: @{message.from_user.username} (ID: {message.from_user.id})\n"
                f"📍 Клуб: Cyberx {club}\n"
                f"📌 {message.caption}",
        parse_mode="Markdown"
    )
    await message.reply("✅ Ваша жалоба отправлена! Администратор скоро ответит.", reply_markup=main_menu)

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: Message):
    if "club" not in user_data.get(message.chat.id, {}):
        await message.reply("❌ Пожалуйста, сначала выберите клуб через /start.")
        return

    await message.reply("❌ Жалоба должна содержать фото. Пожалуйста, прикрепите фото проблемы.", reply_markup=main_menu)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)