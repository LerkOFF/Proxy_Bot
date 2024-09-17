from aiogram.exceptions import TelegramAPIError
import logging

logger = logging.getLogger(__name__)

async def safe_send_message(bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
        logger.info(f"Сообщение отправлено пользователю {chat_id}: {text}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

async def safe_send_photo(bot, chat_id, photo, caption=None, **kwargs):
    try:
        await bot.send_photo(chat_id, photo, caption=caption, **kwargs)
        logger.info(f"Фото отправлено пользователю {chat_id}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка при отправке фото пользователю {chat_id}: {e}")

async def safe_send_document(bot, chat_id, document, caption=None, **kwargs):
    try:
        await bot.send_document(chat_id, document, caption=caption, **kwargs)
        logger.info(f"Документ отправлен пользователю {chat_id}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка при отправке документа пользователю {chat_id}: {e}")
