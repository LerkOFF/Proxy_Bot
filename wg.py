import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class WgEasyAPI:
    def __init__(self, base_url, password):
        self.base_url = base_url
        self.headers = {'Content-Type': 'application/json'}
        self.password = password
        self.session_cookies = None
        logger.info(f"Инициализация API с базовым URL: {self.base_url}")

    def authenticate(self):
        url = f"{self.base_url}/api/session"
        body = {"password": self.password}
        logger.info("Попытка аутентификации...")

        try:
            response = requests.post(url, headers=self.headers, json=body)
            response.raise_for_status()
            self.session_cookies = response.cookies
            logger.info("Аутентификация успешна")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return False

    def create_client(self, chat_id):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед созданием клиента")
            return None

        url = f"{self.base_url}/api/wireguard/client"
        body = {"name": str(chat_id)}
        logger.info(f"Попытка создать клиента с chat_id: {chat_id}")

        try:
            response = requests.post(url, headers=self.headers, json=body, cookies=self.session_cookies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при создании клиента: {e}")
            return None

    def enable_client(self, client_id):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед включением клиента")
            return False

        url = f"{self.base_url}/api/wireguard/client/{client_id}/enable"
        logger.info(f"Попытка включить клиента с ID: {client_id}")

        try:
            response = requests.post(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
            logger.info(f"Клиент {client_id} успешно включён")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при включении клиента {client_id}: {e}")
            return False

    def disable_client(self, chat_id):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед отключением клиента")
            return False

        clients = self.get_clients()
        if not clients:
            return False

        client = next((c for c in clients if c['name'] == str(chat_id)), None)
        if not client:
            logger.error(f"Клиент с chat_id {chat_id} не найден")
            return False

        client_id = client['id']
        url = f"{self.base_url}/api/wireguard/client/{client_id}/disable"

        try:
            response = requests.post(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
            logger.info(f"Клиент {chat_id} успешно отключён")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отключении клиента {chat_id}: {e}")
            return False

    def get_config_client(self, client_id):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед получением конфигурации клиента")
            return None

        url = f"{self.base_url}/api/wireguard/client/{client_id}/configuration"
        logger.info(f"Попытка получить конфигурацию клиента с ID: {client_id}")

        try:
            response = requests.get(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
            config_data = response.text
            return config_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении конфигурации клиента: {e}")
            return None

    def get_clients(self):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед получением списка клиентов")
            return None

        url = f"{self.base_url}/api/wireguard/client"
        logger.info("Попытка получить список клиентов...")

        try:
            response = requests.get(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении списка клиентов: {e}")
            return None

        clients = response.json()
        logger.info(f"Всего клиентов: {len(clients)}")

        for client in clients:
            logger.info(f"Клиент: {client['name']}, IP: {client['address']}, ID: {client['id']}, Создан: {client['createdAt']}")
        return clients

    def remove_client(self, chat_id):
        if not self.session_cookies:
            logger.error("Необходимо выполнить аутентификацию перед удалением клиента")
            return False

        clients = self.get_clients()
        if not clients:
            return False

        client = next((c for c in clients if c['name'] == str(chat_id)), None)
        if not client:
            logger.error(f"Клиент с chat_id {chat_id} не найден среди существующих клиентов WireGuard")
            return False

        client_id = client['id']
        url = f"{self.base_url}/api/wireguard/client/{client_id}"

        logger.info(f"Попытка удалить клиента с ID: {client_id} и chat_id: {chat_id}")

        try:
            response = requests.delete(url, headers=self.headers, cookies=self.session_cookies)
            response.raise_for_status()
            logger.info(f"Клиент {chat_id} успешно удалён из WireGuard (ID: {client_id})")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при удалении клиента {chat_id} из WireGuard: {e}")
            return False
