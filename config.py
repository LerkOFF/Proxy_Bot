from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')

    WG_PASSWORD = os.getenv('WG_PASSWORD')
    WG_QR_SAVE_PATH = os.getenv('WG_QR_SAVE_PATH')

    CLOUDCONVERT_API_KEY = os.getenv('CLOUDCONVERT_API_KEY')
