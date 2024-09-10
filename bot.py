import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from wg import WgEasyAPI
from config import Config
from db import add_user, user_exists

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
wg_api = WgEasyAPI(base_url="http://wg.oai.su:51821", password=Config.WG_PASSWORD)


async def start(update: Update, context):
    chat_id = update.message.chat_id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")

    add_user(chat_id)
    await update.message.reply_text("Привет! Я бот для покупки прокси через WireGuard!")


async def create_client(update: Update, context):
    chat_id = update.message.chat_id

    # Проверяем, существует ли пользователь в базе данных
    if not user_exists(chat_id):
        await update.message.reply_text("Сначала используйте команду /start для регистрации.")
        return

    # Аутентифицируемся в WireGuard API
    wg_api.authenticate()

    # Получаем список клиентов
    clients = wg_api.get_clients()

    # Проверяем, существует ли уже клиент с данным chat_id
    existing_client = next((client for client in clients if client['name'] == str(chat_id)), None)

    if existing_client:
        # Если клиент уже существует, выводим сообщение
        await update.message.reply_text("Вам уже была создана конфигурация.")
        return

    # Создаём нового клиента
    creation_response = wg_api.create_client(chat_id)

    if creation_response and creation_response.get('success'):
        created_client = next((client for client in wg_api.get_clients() if client['name'] == str(chat_id)), None)

        if created_client:
            client_id = created_client['id']
            qr_code = wg_api.get_qr_code(client_id)

            if qr_code:
                await context.bot.send_photo(chat_id, photo=qr_code)
                logger.info(f"QR-код для клиента с chat_id {chat_id} отправлен.")
            else:
                await update.message.reply_text("Не удалось получить QR-код.")
        else:
            await update.message.reply_text("Не удалось найти созданного клиента.")
            logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов.")
    else:
        await update.message.reply_text("Не удалось создать клиента в WireGuard.")
        logger.error(f"Ошибка создания клиента в WireGuard: {creation_response}")


def main():
    logger.info("Запуск бота...")

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_client", create_client))

    application.run_polling()


if __name__ == '__main__':
    main()
