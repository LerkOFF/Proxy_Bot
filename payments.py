import qrcode
import os
from aiogram import types
from aiogram.types import FSInputFile
from db import get_user_by_chat_id, update_user_payment
from wg import WgEasyAPI
from config import Config
import logging

logger = logging.getLogger(__name__)
wg_api = WgEasyAPI(base_url="http://wg.oai.su:51821", password=Config.WG_PASSWORD)

# Указываем путь для сохранения QR-кода
qr_code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qrcodes')

# Убедитесь, что директория для QR-кодов существует
if not os.path.exists(qr_code_dir):
    os.makedirs(qr_code_dir)

async def handle_approval(query: types.CallbackQuery):
    action, chat_id = query.data.split('_')

    if action == "approve":
        user = get_user_by_chat_id(chat_id)
        if user and not user["date_start"]:
            update_user_payment(chat_id)
            wg_api.authenticate()

            # Создаем клиента
            creation_response = wg_api.create_client(chat_id)
            logger.info(f"Ответ от WireGuard API при создании клиента: {creation_response}")

            # Получаем список клиентов
            clients = wg_api.get_clients()
            created_client = next((client for client in clients if client['name'] == str(chat_id)), None)

            if created_client:
                client_id = created_client['id']
                # Получаем конфигурацию клиента
                client_config = wg_api.get_config_client(client_id)

                if client_config:
                    # Генерация QR-кода на основе конфигурации
                    img = qrcode.make(client_config)
                    qr_code_path = os.path.join(qr_code_dir, f"wg_qrcode_{chat_id}.png")

                    # Сохраняем QR-код как изображение в файл
                    img.save(qr_code_path)

                    # Отправляем QR-код как фото
                    qr_code_input = FSInputFile(qr_code_path)
                    await query.message.bot.send_photo(chat_id, qr_code_input, caption="Успешно! Вот ваш QR-код для подключения WireGuard.")

                    # Также отправляем текстовую конфигурацию
                    await query.message.bot.send_message(chat_id, text=f"Вот ваша конфигурация WireGuard:\n\n{client_config}")
                    logger.info(f"Клиент с chat_id {chat_id} одобрен, и QR-код с конфигурацией отправлены.")
                else:
                    await query.message.bot.send_message(chat_id, text="Ошибка при получении конфигурации.")
            else:
                await query.message.bot.send_message(chat_id, text="Не удалось найти созданного клиента.")
                logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов.")
            await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} был одобрен.")
        else:
            await query.message.edit_caption(caption="Ошибка: Пользователь уже имеет оплаченный статус.")
    elif action == "reject":
        await query.message.bot.send_message(chat_id, text="Ошибка. Ваши данные были отклонены.")
        await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} был отклонён.")
