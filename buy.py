import logging
from telegram import ReplyKeyboardMarkup
from config import Config
from db import add_user

# Logging configuration
logger = logging.getLogger(__name__)

# Обработчик для команды /start
async def start(update, context):
    chat_id = update.message.chat_id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")

    # Добавляем пользователя в базу данных
    add_user(chat_id)

    # Создаем клавиатуру с кнопкой "Купить 'Финляндия'"
    keyboard = [["Купить 'Финляндия'"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # Отправляем приветственное сообщение с клавиатурой
    await update.message.reply_text(
        "Привет! Я бот для покупки прокси через WireGuard! Выберите действие:",
        reply_markup=reply_markup
    )

# Обработчик для нажатия кнопки "Купить 'Финляндия'"
async def handle_button_click(update, context):
    chat_id = update.message.chat_id

    if update.message.text == "Купить 'Финляндия'":
        # Отправляем сообщение с инструкцией по оплате
        await update.message.reply_text(
            "Хороший выбор! Переведите ровно 200р на Boosty: https://boosty.to/lerk/donate.\n"
            "После перевода отправьте чек или скриншот подтверждающий это."
        )

# Обработчик для получения фотографий/файлов
async def handle_file_upload(update, context):
    chat_id = update.message.chat_id
    if update.message.photo:
        # Отправка файла владельцу
        owner_id = Config.TELEGRAM_ID
        await context.bot.send_photo(owner_id, photo=update.message.photo[-1].file_id, caption=f"Чек от пользователя {chat_id}")
        await update.message.reply_text("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
        logger.info(f"Пользователь с chat_id {chat_id} отправил фото.")
    elif update.message.document:
        # Отправка файла владельцу
        owner_id = Config.TELEGRAM_ID
        await context.bot.send_document(owner_id, document=update.message.document.file_id, caption=f"Чек от пользователя {chat_id}")
        await update.message.reply_text("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
        logger.info(f"Пользователь с chat_id {chat_id} отправил документ.")
