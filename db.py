import mysql.connector
from mysql.connector import Error
from config import Config

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

# Добавление нового пользователя
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

# Проверка существования пользователя
def user_exists(chat_id):
    connection = create_connection()
    cursor = connection.cursor()

    query = "SELECT COUNT(*) FROM users WHERE chat_id=%s"
    cursor.execute(query, (chat_id,))
    result = cursor.fetchone()[0]

    close_connection(connection)
    return result > 0

# Добавление клиента в таблицу clients
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

# Получение пользователя по chat_id
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
