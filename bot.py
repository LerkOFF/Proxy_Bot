import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from buy import start, buy_server, cancel, handle_file_upload, show_contacts
from db import get_user_state, get_all_users_from_db
from payments import handle_approval
from config import Config
from states import BuyProcess
from logger import logger

async def main():
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(start, F.text == "/start")
    dp.message.register(buy_server, F.text.startswith("Купить "), BuyProcess.Start)
    dp.message.register(cancel, F.text == "Отмена", BuyProcess.Buying)
    dp.message.register(handle_file_upload, F.content_type.in_([types.ContentType.PHOTO, types.ContentType.DOCUMENT]), BuyProcess.Buying)
    dp.message.register(show_contacts, F.text == "Контакты", BuyProcess.Start)

    dp.callback_query.register(handle_approval, F.data.startswith('approve_') | F.data.startswith('reject_'))

    users = get_all_users_from_db()
    for user in users:
        user_id = user['chat_id']
        saved_state = get_user_state(user_id)
        if saved_state:
            key = StorageKey(user_id=user_id, chat_id=user_id, bot_id=bot.id)
            await dp.fsm.storage.set_state(key=key, state=saved_state)
            logger.info(f"Состояние для пользователя {user_id} восстановлено: {saved_state}")

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
