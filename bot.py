
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.storage.memory import MemoryStorage
from buy import start, buy_finland, cancel, handle_file_upload
from payments import handle_approval
from config import Config
from states import BuyProcess

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(start, F.text == "/start")
    dp.message.register(buy_finland, F.text == "Купить 'Финляндия'", BuyProcess.Start)
    dp.message.register(cancel, F.text == "Отмена", BuyProcess.Buying)
    dp.message.register(handle_file_upload, F.content_type.in_([types.ContentType.PHOTO, types.ContentType.DOCUMENT]), BuyProcess.Buying)

    dp.callback_query.register(handle_approval, BuyProcess.WaitingPaymentConfirmation)

    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

