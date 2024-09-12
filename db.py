import mysql.connector
from mysql.connector import Error
from config import Config
from states import BuyProcess


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
            print("Соединение с базой данных установлено")
        return connection
    except Error as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None

def close_connection(connection):
    if connection and connection.is_connected():
        connection.close()
        print("Подключение к базе данных закрыто")

def add_user(chat_id, date_start=None):
    connection = create_connection()
    if connection is None:
        print("Не удалось установить соединение с базой данных")
        return

    cursor = connection.cursor()
    query = """
    INSERT INTO users (chat_id, date_start)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE chat_id=chat_id;
    """
    try:
        cursor.execute(query, (chat_id, date_start))
        connection.commit()
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
    cursor = connection.cursor()

    query = """
    INSERT INTO user_states (chat_id, state) VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE state=%s;
    """
    try:
        state_str = state.state
        cursor.execute(query, (chat_id, state_str, state_str))
        connection.commit()
    except Error as e:
        print(f"Ошибка при установке состояния пользователя: {e}")
    finally:
        close_connection(connection)


def get_user_state(chat_id):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = "SELECT state FROM user_states WHERE chat_id=%s"
    cursor.execute(query, (chat_id,))
    user_state = cursor.fetchone()

    close_connection(connection)

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
