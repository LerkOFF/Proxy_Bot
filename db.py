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

def add_user(chat_id):
    connection = create_connection()
    if connection is None:
        print("Не удалось установить соединение с базой данных")
        return

    cursor = connection.cursor()
    query = """
    INSERT INTO users (chat_id)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE chat_id=chat_id;
    """
    try:
        cursor.execute(query, (chat_id,))
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
