import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from buy import start, handle_button_click, handle_file_upload, handle_approval

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Основная функция для инициализации и запуска бота
def main():
    logger.info("Запуск бота...")

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_click))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_file_upload))
    application.add_handler(CallbackQueryHandler(handle_approval))

    application.run_polling()

if __name__ == '__main__':
    main()
