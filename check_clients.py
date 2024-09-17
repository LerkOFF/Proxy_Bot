import logging
import os
from datetime import datetime
from db import (
    get_db_connection,
    get_clients_to_warn,
    get_clients_to_remove,
    remove_client_from_db
)
from wg import WgEasyAPI
from config import Config
from aiogram import Bot
from utils import safe_send_message
from logger import logger

def remove_qr_code(chat_id, server):
    qr_code_path = os.path.join('qrcodes', f'wg_qrcode_{chat_id}_{server}.png')
    if os.path.exists(qr_code_path):
        try:
            os.remove(qr_code_path)
            logger.info(f"Файл QR-кода {qr_code_path} успешно удалён")
        except Exception as e:
            logger.error(f"Ошибка при удалении QR-кода {qr_code_path}: {e}")
    else:
        logger.warning(f"Файл QR-кода {qr_code_path} не найден для удаления")

async def send_warning_message(bot, chat_id, days_passed, server):
    if days_passed == 31:
        message_text = f"Ваша подписка на сервер {server} закончится через 2 дня. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 32:
        message_text = f"Ваша подписка на сервер {server} закончится завтра. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 33:
        message_text = f"Ваша подписка на сервер {server} закончится сегодня. Оплатите подписку, чтобы избежать отключения."
    else:
        message_text = f"Ваша подписка на сервер {server} скоро закончится. Пожалуйста, оплатите её."

    await safe_send_message(bot, chat_id, message_text)

async def main():
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    servers = {
        'Finland': Config.WG1_SERVER_IP,
        'USA': Config.WG2_SERVER_IP
    }

    wg_apis = {}

    for server, server_ip in servers.items():
        wg_api = WgEasyAPI(base_url=server_ip, password=Config.WG_PASSWORD)
        if not wg_api.authenticate():
            logger.error(f"Не удалось аутентифицироваться в WireGuard API для сервера {server}")
            continue
        wg_apis[server] = wg_api

    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось подключиться к базе данных")
            return

        try:
            for server, wg_api in wg_apis.items():
                clients_to_warn = get_clients_to_warn(connection, days=30, buffer_days=3, server=server)
                logger.info(f"Найдено {len(clients_to_warn)} клиентов для предупреждения на сервере {server}")

                for client in clients_to_warn:
                    user_id = client['user_id']
                    chat_id = user_id
                    date_payed = client['date_payed']
                    days_passed = (datetime.now() - date_payed).days

                    logger.info(f"Предупреждение клиента {user_id} на сервере {server}, прошло {days_passed} дней")

                    if wg_api.disable_client(user_id):
                        logger.info(f"Клиент {user_id} на сервере {server} отключён")
                    else:
                        logger.error(f"Не удалось отключить клиента {user_id} на сервере {server}")
                    await send_warning_message(bot, chat_id, days_passed, server)

                clients_to_remove = get_clients_to_remove(connection, days=33, server=server)
                logger.info(f"Найдено {len(clients_to_remove)} клиентов для удаления на сервере {server}")

                for user_id in clients_to_remove:
                    chat_id = user_id
                    logger.info(f"Удаление клиента {user_id} на сервере {server}")

                    if wg_api.remove_client(user_id):
                        logger.info(f"Клиент {user_id} на сервере {server} удалён через API")
                        remove_qr_code(chat_id, server)
                    else:
                        logger.error(f"Не удалось удалить клиента {user_id} на сервере {server} через API")

                    message_text = f"Подписка на сервер {server} закончилась и Вы не успели её оплатить, конфигурация была удалена."
                    await safe_send_message(bot, chat_id, message_text)

                    remove_client_from_db(connection, user_id, server)

        finally:
            logger.info("Завершение работы check_clients.py")
            await bot.close()

if __name__ == '__main__':
    import asyncio
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    asyncio.run(main())
