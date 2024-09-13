import logging
from datetime import datetime, timedelta

import mysql.connector
from mysql.connector import Error
from config import Config
from states import BuyProcess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_connection():
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
        return connection
    except Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

def close_connection(connection):
    if connection and connection.is_connected():
        connection.close()
        logger.info("Подключение к базе данных закрыто")

def add_user(chat_id, date_start=None):
    if date_start is None:
        date_start = datetime.now()

    connection = create_connection()
    if connection is None:
        print("Не удалось установить соединение с базой данных")
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
        print(f"Пользователь с chat_id {chat_id} добавлен/обновлён")
    except Error as e:
        print(f"Ошибка при добавлении пользователя: {e}")
    finally:
        close_connection(connection)


def user_exists(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = "SELECT COUNT(*) FROM users WHERE chat_id=%s"
    cursor.execute(query, (chat_id,))
    result = cursor.fetchone()[0]

    close_connection(connection)
    return result > 0

def add_client(user_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = "INSERT INTO clients (user_id, date_payed) VALUES (%s, NOW())"
    try:
        cursor.execute(query, (user_id,))
        connection.commit()
    except Error as e:
        print(f"Ошибка при добавлении клиента: {e}")
    finally:
        close_connection(connection)

def get_user_by_chat_id(chat_id):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = "SELECT * FROM users WHERE chat_id=%s"
    cursor.execute(query, (chat_id,))
    user = cursor.fetchone()

    close_connection(connection)
    return user


def update_user_payment(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    try:
        query_user = "SELECT chat_id FROM users WHERE chat_id=%s"
        cursor.execute(query_user, (chat_id,))
        user = cursor.fetchone()

        if not user:
            print(f"Пользователь с chat_id {chat_id} не найден.")
            return

        query_add_client = "INSERT INTO clients (user_id, date_payed) VALUES (%s, NOW())"
        cursor.execute(query_add_client, (chat_id,))

        connection.commit()
        print(f"Оплата для пользователя с chat_id {chat_id} обновлена.")
    except Error as e:
        print(f"Ошибка при обновлении платежа пользователя: {e}")
    finally:
        close_connection(connection)


def set_user_state(chat_id, state):
    connection = create_connection()
    if connection is None:
        print("Не удалось установить соединение с базой данных")
        return
    query_get_user_id = """
    SELECT chat_id FROM users WHERE chat_id=%s
    """

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
                print(f"Состояние пользователя {user_id} установлено как {state_str}")
            else:
                print(f"Пользователь с chat_id {chat_id} не найден.")
    except Error as e:
        print(f"Ошибка при установке состояния пользователя: {e}")
    finally:
        close_connection(connection)


def get_user_state(chat_id):
    connection = create_connection()
    if connection is None:
        print("Не удалось установить соединение с базой данных")
        return None

    # Получаем user_id (chat_id) из таблицы users
    query_get_user_id = """
    SELECT chat_id FROM users WHERE chat_id=%s
    """

    query_get_state = """
    SELECT state FROM user_states WHERE user_id=%s
    """

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
                    if state_str == "BuyProcess:Start":
                        return BuyProcess.Start
                    elif state_str == "BuyProcess:Buying":
                        return BuyProcess.Buying
                    elif state_str == "BuyProcess:WaitingAnswer":
                        return BuyProcess.WaitingAnswer
                    elif state_str == "BuyProcess:WaitingPaymentConfirmation":
                        return BuyProcess.WaitingPaymentConfirmation
            else:
                print(f"Пользователь с chat_id {chat_id} не найден.")
    except Error as e:
        print(f"Ошибка при получении состояния пользователя: {e}")
    finally:
        close_connection(connection)

    return None


def reset_user_state(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = "DELETE FROM user_states WHERE chat_id=%s"
    cursor.execute(query, (chat_id,))
    connection.commit()

    close_connection(connection)


def get_all_users_from_db():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = "SELECT chat_id FROM users"
    cursor.execute(query)
    users = cursor.fetchall()

    close_connection(connection)
    return users

def is_payment_recent(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = """
    SELECT date_payed FROM clients
    WHERE user_id=%s
    ORDER BY date_payed DESC
    LIMIT 1;
    """
    try:
        cursor.execute(query, (chat_id,))
        result = cursor.fetchone()
        if result:
            last_payment_date = result[0]
            if last_payment_date >= datetime.now() - timedelta(days=30):
                return True
    except Error as e:
        print(f"Ошибка при проверке оплаты: {e}")
    finally:
        close_connection(connection)

    return False

def get_last_payment_date(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = """
    SELECT date_payed FROM clients
    WHERE user_id=%s
    ORDER BY date_payed DESC
    LIMIT 1;
    """
    try:
        cursor.execute(query, (chat_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
    except Error as e:
        print(f"Ошибка при получении даты последней оплаты: {e}")
    finally:
        close_connection(connection)

    return None
