# db.py
import logging
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from config import Config
from states import BuyProcess

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        if connection.is_connected():
            logger.info("Соединение с базой данных установлено")
        yield connection
    except Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        yield None
    finally:
        if connection and connection.is_connected():
            connection.close()
            logger.info("Подключение к базе данных закрыто")

def add_user(chat_id, date_start=None):
    if date_start is None:
        date_start = datetime.now()

    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return

        query = """
        INSERT INTO users (chat_id, date_start)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE chat_id=chat_id;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id, date_start))
            connection.commit()
            logger.info(f"Пользователь с chat_id {chat_id} добавлен/обновлён")
        except Error as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")

def user_exists(chat_id):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return False

        query = "SELECT COUNT(*) FROM users WHERE chat_id=%s"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id,))
                result = cursor.fetchone()[0]
            return result > 0
        except Error as e:
            logger.error(f"Ошибка при проверке существования пользователя: {e}")
            return False

def add_client(user_id, server):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return

        query = "INSERT INTO clients (user_id, date_payed, server) VALUES (%s, NOW(), %s)"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (user_id, server))
            connection.commit()
            logger.info(f"Клиент с user_id {user_id} добавлен на сервер {server}")
        except Error as e:
            logger.error(f"Ошибка при добавлении клиента: {e}")

def get_user_by_chat_id(chat_id):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return None

        query = "SELECT * FROM users WHERE chat_id=%s"
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (chat_id,))
                user = cursor.fetchone()
            return user
        except Error as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None

def update_user_payment(chat_id, server):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return

        try:
            query_user = "SELECT chat_id FROM users WHERE chat_id=%s"
            with connection.cursor() as cursor:
                cursor.execute(query_user, (chat_id,))
                user = cursor.fetchone()

                if not user:
                    logger.warning(f"Пользователь с chat_id {chat_id} не найден.")
                    return

                query_add_client = "INSERT INTO clients (user_id, date_payed, server) VALUES (%s, NOW(), %s)"
                cursor.execute(query_add_client, (chat_id, server))
            connection.commit()
            logger.info(f"Оплата для пользователя с chat_id {chat_id} на сервер {server} обновлена.")
        except Error as e:
            logger.error(f"Ошибка при обновлении платежа пользователя: {e}")

def set_user_state(chat_id, state):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return

        query_get_user_id = "SELECT chat_id FROM users WHERE chat_id=%s"
        query_insert_state = """
        INSERT INTO user_states (user_id, state) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE state=%s;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query_get_user_id, (chat_id,))
                result = cursor.fetchone()

                if result:
                    user_id = result[0]
                    state_str = state.state
                    cursor.execute(query_insert_state, (user_id, state_str, state_str))
                    connection.commit()
                    logger.info(f"Состояние пользователя {user_id} установлено как {state_str}")
                else:
                    logger.warning(f"Пользователь с chat_id {chat_id} не найден.")
        except Error as e:
            logger.error(f"Ошибка при установке состояния пользователя: {e}")

def get_user_state(chat_id):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return None

        query_get_user_id = "SELECT chat_id FROM users WHERE chat_id=%s"
        query_get_state = "SELECT state FROM user_states WHERE user_id=%s"
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query_get_user_id, (chat_id,))
                result = cursor.fetchone()

                if result:
                    user_id = result['chat_id']
                    cursor.execute(query_get_state, (user_id,))
                    user_state = cursor.fetchone()

                    if user_state:
                        state_str = user_state['state']
                        # Преобразование строки состояния обратно в объект состояния
                        if state_str == "BuyProcess:Start":
                            return BuyProcess.Start
                        elif state_str == "BuyProcess:Buying":
                            return BuyProcess.Buying
                        elif state_str == "BuyProcess:WaitingAnswer":
                            return BuyProcess.WaitingAnswer
                        elif state_str == "BuyProcess:WaitingPaymentConfirmation":
                            return BuyProcess.WaitingPaymentConfirmation
            return None
        except Error as e:
            logger.error(f"Ошибка при получении состояния пользователя: {e}")
            return None

def reset_user_state(chat_id):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return

        query = "DELETE FROM user_states WHERE user_id=%s"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id,))
            connection.commit()
            logger.info(f"Состояние пользователя {chat_id} сброшено")
        except Error as e:
            logger.error(f"Ошибка при сбросе состояния пользователя: {e}")

def get_all_users_from_db():
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return []

        query = "SELECT chat_id FROM users"
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
            return users
        except Error as e:
            logger.error(f"Ошибка при получении всех пользователей: {e}")
            return []

def is_payment_recent(chat_id, server, days=30):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return False

        query = """
        SELECT date_payed FROM clients
        WHERE user_id=%s AND server=%s
        ORDER BY date_payed DESC
        LIMIT 1;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id, server))
                result = cursor.fetchone()
                if result:
                    last_payment_date = result[0]
                    if last_payment_date >= datetime.now() - timedelta(days=days):
                        return True
            return False
        except Error as e:
            logger.error(f"Ошибка при проверке оплаты: {e}")
            return False

def get_last_payment_date(chat_id, server):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return None

        query = """
        SELECT date_payed FROM clients
        WHERE user_id=%s AND server=%s
        ORDER BY date_payed DESC
        LIMIT 1;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id, server))
                result = cursor.fetchone()
                if result:
                    return result[0]
            return None
        except Error as e:
            logger.error(f"Ошибка при получении даты последней оплаты: {e}")
            return None

def user_already_has_subscription(chat_id, server):
    with get_db_connection() as connection:
        if connection is None:
            logger.error("Не удалось установить соединение с базой данных")
            return False

        query = """
        SELECT * FROM clients
        WHERE user_id = %s AND server = %s
        AND date_payed > NOW() - INTERVAL 30 DAY
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (chat_id, server))
                result = cursor.fetchone()
                return result is not None
        except Error as e:
            logger.error(f"Ошибка при проверке подписки: {e}")
            return False

# Добавленные функции для check_clients.py

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
    except Error as e:
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
    except Error as e:
        logger.error(f"Ошибка при получении клиентов для удаления: {e}")
        return []
    finally:
        cursor.close()

def remove_client_from_db(connection, user_id, server):
    cursor = connection.cursor()
    query = "DELETE FROM clients WHERE user_id=%s AND server=%s"
    try:
        cursor.execute(query, (user_id, server))
        connection.commit()
        logger.info(f"Клиент с user_id {user_id} на сервере {server} удалён из базы данных")
    except Error as e:
        logger.error(f"Ошибка при удалении клиента из базы данных: {e}")
    finally:
        cursor.close()
