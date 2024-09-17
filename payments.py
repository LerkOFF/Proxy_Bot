from datetime import datetime
import qrcode
import os
from aiogram import types
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from config import Config
from states import BuyProcess
from db import get_user_by_chat_id, update_user_payment, set_user_state, get_last_payment_date
from wg import WgEasyAPI
from keyboards import get_main_menu_keyboard
from utils import safe_send_message, safe_send_photo
from logger import logger

qr_code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qrcodes')

if not os.path.exists(qr_code_dir):
    os.makedirs(qr_code_dir)

async def handle_approval(query: types.CallbackQuery, state: FSMContext):
    parts = query.data.split('_')
    if len(parts) != 3:
        await query.answer("Неверный формат данных.")
        logger.warning("Получены некорректные данные в callback_query")
        return

    action, chat_id, server = parts

    server_ip = Config.WG1_SERVER_IP if server == 'Finland' else Config.WG2_SERVER_IP if server == 'USA' else None

    if server_ip is None:
        await query.answer("Неизвестный сервер.")
        logger.warning(f"Неизвестный сервер в callback_query: {server}")
        return

    wg_api = WgEasyAPI(base_url=server_ip, password=Config.WG_PASSWORD)

    if action == "approve":
        user = get_user_by_chat_id(chat_id)
        if user:
            last_payment_date = get_last_payment_date(chat_id, server)
            if last_payment_date:
                days_passed = (datetime.now() - last_payment_date).days

                if 30 <= days_passed <= 33:
                    if wg_api.authenticate():
                        clients = wg_api.get_clients()
                        existing_client = next((client for client in clients if client['name'] == str(chat_id)), None)

                        if existing_client:
                            client_id = existing_client['id']

                            enable_response = wg_api.enable_client(client_id)
                            if enable_response:
                                await safe_send_message(query.message.bot, chat_id,
                                                        "Ваша подписка продлена, клиент WireGuard был включён.")
                                logger.info(f"Клиент с chat_id {chat_id} был повторно включён в WireGuard.")
                                # Необходимо обновить состояние пользователя
                                await state.set_state(BuyProcess.Start)
                                set_user_state(chat_id, BuyProcess.Start)
                                return
                            else:
                                await safe_send_message(query.message.bot, chat_id,
                                                        "Не удалось включить клиента, будет создан новый.")
                                logger.warning(f"Не удалось включить клиента с chat_id {chat_id}, создаём нового.")

        update_user_payment(chat_id, server)
        if wg_api.authenticate():
            creation_response = wg_api.create_client(chat_id)
            logger.info(f"Ответ от WireGuard API при создании клиента: {creation_response}")

            clients = wg_api.get_clients()
            created_client = next((client for client in clients if client['name'] == str(chat_id)), None)

            if created_client:
                client_id = created_client['id']
                client_config = wg_api.get_config_client(client_id)

                if client_config:
                    img = qrcode.make(client_config)
                    qr_code_path = os.path.join(qr_code_dir, f"wg_qrcode_{chat_id}_{server}.png")

                    img.save(qr_code_path)

                    qr_code_input = FSInputFile(qr_code_path)
                    await safe_send_photo(query.message.bot, chat_id, qr_code_input,
                                         caption="Успешно! Вот ваш QR-код для подключения WireGuard.")

                    await safe_send_message(query.message.bot, chat_id,
                                            f"Вот ваша конфигурация WireGuard для сервера {server}:\n\n{client_config}")
                    logger.info(f"Клиент с chat_id {chat_id} одобрен на сервере {server}, и QR-код с конфигурацией отправлены.")
                else:
                    await safe_send_message(query.message.bot, chat_id, "Ошибка при получении конфигурации.")
                    logger.error(f"Ошибка при получении конфигурации для клиента {chat_id}")
            else:
                await safe_send_message(query.message.bot, chat_id, "Не удалось найти созданного клиента.")
                logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов на сервере {server}.")

            await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} на сервер {server} был одобрен.")

            await state.set_state(BuyProcess.Start)
            set_user_state(chat_id, BuyProcess.Start)

            keyboard = get_main_menu_keyboard()
            await safe_send_message(query.message.bot, chat_id, "Вы можете снова выбрать действие.",
                                    reply_markup=keyboard)

        else:
            await safe_send_message(query.message.bot, chat_id, "Не удалось аутентифицироваться в WireGuard API.")
            logger.error(f"Не удалось аутентифицироваться в WireGuard API для сервера {server}")

    elif action == "reject":
        await safe_send_message(query.message.bot, chat_id,
                                "Ошибка. Ваши данные были отклонены. Если что-то не так, свяжитесь по почте lerk@joulerk.ru")
        await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} на сервер {server} был отклонён.")
        logger.info(f"Платёж пользователя {chat_id} на сервер {server} отклонён.")

        await state.set_state(BuyProcess.Start)
        set_user_state(chat_id, BuyProcess.Start)

        keyboard = get_main_menu_keyboard()
        await safe_send_message(query.message.bot, chat_id, "Вы можете снова выбрать действие.", reply_markup=keyboard)
