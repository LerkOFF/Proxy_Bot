from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from db import update_user_payment, get_user_by_chat_id, add_user
from wg import WgEasyAPI
from config import Config
import logging

logger = logging.getLogger(__name__)
wg_api = WgEasyAPI(base_url="http://wg.oai.su:51821", password=Config.WG_PASSWORD)

async def start(update, context):
    chat_id = update.message.chat_id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")
    add_user(chat_id)

    keyboard = [["Купить 'Финляндия'"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я бот для покупки прокси через WireGuard! Выберите действие:",
        reply_markup=reply_markup
    )

async def handle_button_click(update, context):
    chat_id = update.message.chat_id
    if update.message.text == "Купить 'Финляндия'":
        await update.message.reply_text(
            "Хороший выбор! Переведите ровно 200р на Boosty: https://boosty.to/lerk/donate.\n"
            "После перевода отправьте чек или скриншот подтверждающий это."
        )

async def handle_file_upload(update, context):
    chat_id = update.message.chat_id
    if update.message.photo:
        owner_id = Config.TELEGRAM_ID
        keyboard = [
            [InlineKeyboardButton("Одобрить", callback_data=f"approve_{chat_id}"),
             InlineKeyboardButton("Отклонить", callback_data=f"reject_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(owner_id, photo=update.message.photo[-1].file_id, caption=f"Чек от пользователя {chat_id}", reply_markup=reply_markup)
        await update.message.reply_text("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
        logger.info(f"Пользователь с chat_id {chat_id} отправил фото.")
    elif update.message.document:
        owner_id = Config.TELEGRAM_ID
        keyboard = [
            [InlineKeyboardButton("Одобрить", callback_data=f"approve_{chat_id}"),
             InlineKeyboardButton("Отклонить", callback_data=f"reject_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_document(owner_id, document=update.message.document.file_id, caption=f"Чек от пользователя {chat_id}", reply_markup=reply_markup)
        await update.message.reply_text("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
        logger.info(f"Пользователь с chat_id {chat_id} отправил документ.")

async def handle_approval(update, context):
    query = update.callback_query
    action, chat_id = query.data.split('_')

    if action == "approve":
        user = get_user_by_chat_id(chat_id)
        if user and not user["IsPayed"]:
            update_user_payment(chat_id, True)
            wg_api.authenticate()
            creation_response = wg_api.create_client(chat_id)
            logger.info(f"Ответ от WireGuard API при создании клиента: {creation_response}")

            clients = wg_api.get_clients()
            created_client = next((client for client in clients if client['name'] == str(chat_id)), None)

            if created_client:
                client_id = created_client['id']
                qr_code = wg_api.get_qr_code(client_id)
                if qr_code:
                    await context.bot.send_photo(chat_id, photo=qr_code, caption="Успешно! Вот qrcode для подключения WireGuard")
                    logger.info(f"Клиент с chat_id {chat_id} одобрен и получен QR-код.")
                else:
                    await context.bot.send_message(chat_id, text="Ошибка при генерации QR-кода.")
            else:
                await context.bot.send_message(chat_id, text="Не удалось найти созданного клиента.")
                logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов.")
            await query.edit_message_caption(caption=f"Платёж пользователя {chat_id} был одобрен.")
        else:
            await query.edit_message_caption(caption="Ошибка: Пользователь уже имеет оплаченный статус.")
    elif action == "reject":
        await context.bot.send_message(chat_id, text="Ошибка. Ваши данные были отклонены, попробуйте связаться с нами по - lerk@joulerk.ru")
        await query.edit_message_caption(caption=f"Платёж пользователя {chat_id} был отклонён.")

