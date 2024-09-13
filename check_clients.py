# check_clients.py
import logging
import os
from datetime import datetime, timedelta
from db import create_connection, close_connection
from wg import WgEasyAPI
from config import Config
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_clients_to_warn(connection, days=30, buffer_days=3, server=None):
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT user_id, date_payed
    FROM clients
    WHERE date_payed <= NOW() - INTERVAL %s DAY
      AND date_payed > NOW() - INTERVAL %s DAY
      AND server = %s
    """
    try:
        cursor.execute(query, (days, days + buffer_days, server))
        clients = cursor.fetchall()
        return clients
    except Exception as e:
        logger.error(f"Ошибка при получении клиентов для предупреждения: {e}")
        return []
    finally:
        cursor.close()

def get_clients_to_remove(connection, days=33, server=None):
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT user_id
    FROM clients
    WHERE date_payed <= NOW() - INTERVAL %s DAY
    AND server = %s
    """
    try:
        cursor.execute(query, (days, server))
        clients = cursor.fetchall()
        return [client['user_id'] for client in clients]
    except Exception as e:
        logger.error(f"Ошибка при получении клиентов для удаления: {e}")
        return []
    finally:
        cursor.close()

async def send_warning_message(bot, chat_id, days_passed, server):
    if days_passed == 31:
        message_text = f"Ваша подписка на сервер {server} закончится через 2 дня. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 32:
        message_text = f"Ваша подписка на сервер {server} закончится завтра. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 33:
        message_text = f"Ваша подписка на сервер {server} закончится сегодня. Оплатите подписку, чтобы избежать отключения."
    else:
        message_text = f"Ваша подписка на сервер {server} скоро закончится. Пожалуйста, оплатите её."

    await send_message(bot, chat_id, message_text)

async def remove_client_from_db(connection, user_id, server):
    cursor = connection.cursor()
    query = "DELETE FROM clients WHERE user_id = %s AND server = %s"
    try:
        cursor.execute(query, (user_id, server))
        connection.commit()
        logger.info(f"Клиент с user_id {user_id} на сервере {server} удалён из базы данных")
    except Exception as e:
        logger.error(f"Ошибка при удалении клиента из базы данных: {e}")
    finally:
        cursor.close()

async def send_message(bot, chat_id, text):
    try:
        await bot.send_message(chat_id, text)
        logger.info(f"Сообщение отправлено пользователю {chat_id}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

async def main():
    async with Bot(token=Config.TELEGRAM_BOT_TOKEN) as bot:
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

        connection = create_connection()
        if not connection:
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
                    await send_message(bot, chat_id, message_text)

                    await remove_client_from_db(connection, user_id, server)

        finally:
            close_connection(connection)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
