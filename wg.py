import base64
import requests
import logging
import cloudconvert
import os
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class WgEasyAPI:
    def __init__(self, base_url, password):
        self.base_url = base_url
        self.headers = {'Content-Type': 'application/json'}
        self.password = password
        self.session_cookies = None
        self.cloudconvert_api_key = Config.CLOUDCONVERT_API_KEY
        logging.info(f"Инициализация API с базовым URL: {self.base_url}")

    def authenticate(self):
        url = f"{self.base_url}/api/session"
        body = {"password": self.password}
        logging.info("Попытка аутентификации...")

        try:
            response = requests.post(url, headers=self.headers, json=body)
            response.raise_for_status()
            self.session_cookies = response.cookies
            logging.info("Аутентификация успешна")
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка аутентификации: {e}")
            return None

    def create_client(self, chat_id):
        if not self.session_cookies:
            logging.error("Невозможно создать клиента без аутентификации")
            return None

        url = f"{self.base_url}/api/wireguard/client"
        body = {"name": str(chat_id)}  # Используем chat_id как имя клиента
        logging.info(f"Попытка создать клиента с chat_id: {chat_id}")

        try:
            response = requests.post(url, headers=self.headers, json=body, cookies=self.session_cookies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при создании клиента: {e}")
            return None

    def get_qr_code(self, client_id):
        if not self.session_cookies:
            logging.error("Необходимо выполнить аутентификацию перед получением QR-кода")
            return None

        url = f"{self.base_url}/api/wireguard/client/{client_id}/qrcode.svg"
        logging.info(f"Попытка получить QR-код клиента с ID: {client_id}")

        try:
            response = requests.get(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при получении QR-кода: {e}")
            return None

        svg_data = response.content

        # Конвертируем SVG в PNG через CloudConvert API
        return self.convert_svg_to_png(svg_data)

    def convert_svg_to_png(self, svg_data):
        cloudconvert.configure(api_key=self.cloudconvert_api_key)

        # Преобразуем SVG в base64
        svg_data_base64 = base64.b64encode(svg_data).decode('utf-8')

        # Создаем задачу для конвертации файла через CloudConvert
        job = cloudconvert.Job.create(payload={
            "tasks": {
                'import-svg': {
                    'operation': 'import/base64',
                    'file': svg_data_base64,  # Base64 закодированные данные
                    'filename': 'client_qrcode.svg'  # Имя файла необходимо для CloudConvert
                },
                'convert': {
                    'operation': 'convert',
                    'input': 'import-svg',
                    'output_format': 'png',
                },
                'export-url': {
                    'operation': 'export/url',
                    'input': 'convert'
                }
            }
        })

        # Ожидаем завершения конвертации
        job = cloudconvert.Job.wait(job['id'])

        export_task = next(task for task in job['tasks'] if task['name'] == 'export-url')
        file_url = export_task['result']['files'][0]['url']

        # Загружаем PNG файл
        png_response = requests.get(file_url)
        png_data = png_response.content

        return png_data


    def get_clients(self):
        if not self.session_cookies:
            logging.error("Необходимо выполнить аутентификацию перед получением списка клиентов")
            return None

        url = f"{self.base_url}/api/wireguard/client"
        logging.info("Попытка получить список клиентов...")

        try:
            response = requests.get(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при получении списка клиентов: {e}")
            return None

        clients = response.json()
        logging.info(f"Всего клиентов: {len(clients)}")

        for client in clients:
            logging.info(
                f"Клиент: {client['name']}, IP: {client['address']}, ID: {client['id']}, Создан: {client['createdAt']}")

        return clients

