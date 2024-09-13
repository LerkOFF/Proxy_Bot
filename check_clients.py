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

def remove_qr_code(chat_id):
    qr_code_path = os.path.join('qrcodes', f'wg_qrcode_{chat_id}.png')
    if os.path.exists(qr_code_path):
        try:
            os.remove(qr_code_path)
            logger.info(f"Файл QR-кода {qr_code_path} успешно удалён")
        except Exception as e:
            logger.error(f"Ошибка при удалении QR-кода {qr_code_path}: {e}")
    else:
        logger.warning(f"Файл QR-кода {qr_code_path} не найден для удаления")

def get_clients_to_warn(connection, days=30, buffer_days=3):
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT user_id, date_payed
    FROM clients
    WHERE date_payed <= NOW() - INTERVAL %s DAY
      AND date_payed > NOW() - INTERVAL %s DAY;
    """
    try:
        cursor.execute(query, (days, days + buffer_days))
        clients = cursor.fetchall()
        return clients
    except Exception as e:
        logger.error(f"Ошибка при получении клиентов для предупреждения: {e}")
        return []
    finally:
        cursor.close()

def get_clients_to_remove(connection, days=33):
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT user_id
    FROM clients
    WHERE date_payed <= NOW() - INTERVAL %s DAY;
    """
    try:
        cursor.execute(query, (days,))
        clients = cursor.fetchall()
        return [client['user_id'] for client in clients]
    except Exception as e:
        logger.error(f"Ошибка при получении клиентов для удаления: {e}")
        return []
    finally:
        cursor.close()

async def send_warning_message(bot, chat_id, days_passed):
    if days_passed == 31:
        message_text = "Ваша подписка закончится через 2 дня. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 32:
        message_text = "Ваша подписка закончится завтра. Оплатите подписку, чтобы избежать отключения."
    elif days_passed == 33:
        message_text = "Ваша подписка закончится сегодня. Оплатите подписку, чтобы избежать отключения."
    else:
        message_text = "Ваша подписка скоро закончится. Пожалуйста, оплатите её."

    await send_message(bot, chat_id, message_text)


async def remove_client_from_db(connection, user_id):
    cursor = connection.cursor()
    query = "DELETE FROM clients WHERE user_id = %s"
    try:
        cursor.execute(query, (user_id,))
        connection.commit()
        logger.info(f"Клиент с user_id {user_id} удалён из базы данных")
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
        wg_api = WgEasyAPI(base_url="http://wg.oai.su:51821", password=Config.WG_PASSWORD)
        if not wg_api.authenticate():
            logger.error("Не удалось аутентифицироваться в WireGuard API")
            return

        connection = create_connection()
        if not connection:
            logger.error("Не удалось подключиться к базе данных")
            return

        try:
            clients_to_warn = get_clients_to_warn(connection, days=30, buffer_days=3)
            logger.info(f"Найдено {len(clients_to_warn)} клиентов для предупреждения")

            for client in clients_to_warn:
                user_id = client['user_id']
                chat_id = user_id
                date_payed = client['date_payed']
                days_passed = (datetime.now() - date_payed).days

                logger.info(f"Предупреждение клиента {user_id}, прошло {days_passed} дней")

                if wg_api.disable_client(user_id):
                    logger.info(f"Клиент {user_id} отключён")
                else:
                    logger.error(f"Не удалось отключить клиента {user_id}")
                await send_warning_message(bot, chat_id, days_passed)

            clients_to_remove = get_clients_to_remove(connection, days=33)
            logger.info(f"Найдено {len(clients_to_remove)} клиентов для удаления")

            for user_id in clients_to_remove:
                chat_id = user_id
                logger.info(f"Удаление клиента {user_id}")

                if wg_api.remove_client(user_id):
                    logger.info(f"Клиент {user_id} удалён через API")

                    remove_qr_code(chat_id)
                else:
                    logger.error(f"Не удалось удалить клиента {user_id} через API")

                message_text = "Подписка закончилась и Вы не успели её оплатить, конфигурация была удалена."
                await send_message(bot, chat_id, message_text)

                await remove_client_from_db(connection, user_id)

        finally:
            close_connection(connection)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
