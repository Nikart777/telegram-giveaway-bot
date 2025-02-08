import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Функция загрузки секретов (GitHub Secrets, Docker Secrets, .env)
def get_secret(name, default=None):
    """Получает секрет из переменных окружения, Docker Secrets или возвращает значение по умолчанию."""
    try:
        # Если запущено в Docker — читаем из /run/secrets/
        secret_path = f"/run/secrets/{name}"
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                return f.read().strip()
        # Иначе загружаем из переменных окружения (GitHub Secrets, .env)
        return os.getenv(name, default)
    except Exception as e:
        logging.error(f"Ошибка при загрузке секрета {name}: {e}")
        return default

# Загружаем токен и ID админа
BOT_TOKEN = get_secret("BOT_TOKEN")
ADMIN_ID = int(get_secret("ADMIN_ID", 0))

# Проверяем, загружены ли секреты
if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("❌ Ошибка: BOT_TOKEN или ADMIN_ID не загружены!")

# Настраиваем бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Логирование
logging.basicConfig(level=logging.INFO)

# Инструкция для пользователей
START_TEXT = (
    "👋 Привет! Этот бот принимает жалобы на ПК.\n\n"
    "📌 Чтобы оставить жалобу, отправьте:\n"
    "1️⃣ Номер ПК\n"
    "2️⃣ Описание проблемы\n"
    "3️⃣ Обязательно фото ошибки\n\n"
    "⚠️ *Важно! Сперва обратитесь к администратору, но если он не помог или вообще бездействовал смело отправляйте.*"
)

# Клавиатура с подтверждением
confirm_keyboard = InlineKeyboardMarkup(row_width=2)
confirm_keyboard.add(
    InlineKeyboardButton("✅ Да, админ не помог", callback_data="confirm"),
    InlineKeyboardButton("❌ Отмена", callback_data="cancel")
)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: Message):
    await message.answer(START_TEXT)

# Словарь для хранения сообщений перед подтверждением
pending_reports = {}

# Обработчик сообщений с фото
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: Message):
    if not message.caption:
        await message.reply("❌ Пожалуйста, добавьте описание проблемы вместе с фото.")
        return

    # Сохраняем жалобу во временный список
    pending_reports[message.chat.id] = {
        "photo": message.photo[-1].file_id,
        "text": message.caption,
        "user": message.from_user
    }

    # Запрашиваем подтверждение у пользователя
    await message.reply(
        "⚠️ Подтвердите, что вы уже обращались к администратору, но он не решил проблему.",
        reply_markup=confirm_keyboard
    )

# Обработчик кнопок
@dp.callback_query_handler(lambda c: c.data in ["confirm", "cancel"])
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id

    if callback_query.data == "confirm":
        # Проверяем, есть ли жалоба в списке
        if user_id in pending_reports:
            report = pending_reports.pop(user_id)

            # Отправляем жалобу админу
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=report["photo"],
                caption=f"🔴 *Новая жалоба*\n\n"
                        f"👨‍💻 От: @{report['user'].username} (ID: {report['user'].id})\n"
                        f"📌 {report['text']}\n\n"
                        f"⚠️ Пользователь подтвердил, что администратор бездействовал.",
                parse_mode="Markdown"
            )
            await callback_query.message.answer("✅ Ваша жалоба отправлена! Администратор скоро ответит.")
        else:
            await callback_query.message.answer("❌ Ошибка: жалоба не найдена.")

    elif callback_query.data == "cancel":
        # Пользователь отменил отправку
        pending_reports.pop(user_id, None)
        await callback_query.message.answer("🚫 Жалоба отменена.")

    await callback_query.answer()

# Обработчик текстовых сообщений без фото
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: Message):
    await message.reply("❌ Жалоба должна содержать фото. Пожалуйста, прикрепите фото проблемы.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
