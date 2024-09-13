# payments.py
from datetime import datetime

import qrcode
import os
from aiogram import types
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from db import get_user_by_chat_id, update_user_payment, set_user_state, get_last_payment_date
from wg import WgEasyAPI
from config import Config
from states import BuyProcess
import logging

logger = logging.getLogger(__name__)

qr_code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qrcodes')

if not os.path.exists(qr_code_dir):
    os.makedirs(qr_code_dir)

async def handle_approval(query: types.CallbackQuery, state: FSMContext):
    parts = query.data.split('_')
    if len(parts) != 3:
        await query.answer("Неверный формат данных.")
        return

    action, chat_id, server = parts

    if server == 'Finland':
        server_ip = Config.WG1_SERVER_IP
    elif server == 'USA':
        server_ip = Config.WG2_SERVER_IP
    else:
        await query.answer("Неизвестный сервер.")
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
                                await query.message.bot.send_message(chat_id,
                                                                     "Ваша подписка продлена, клиент WireGuard был включён.")
                                logger.info(f"Клиент с chat_id {chat_id} был повторно включён в WireGuard.")
                                return
                            else:
                                await query.message.bot.send_message(chat_id, "Не удалось включить клиента, будет создан новый.")
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
                        await query.message.bot.send_photo(chat_id, qr_code_input,
                                                           caption="Успешно! Вот ваш QR-код для подключения WireGuard.")

                        await query.message.bot.send_message(chat_id,
                                                             text=f"Вот ваша конфигурация WireGuard для сервера {server}:\n\n{client_config}")
                        logger.info(f"Клиент с chat_id {chat_id} одобрен на сервере {server}, и QR-код с конфигурацией отправлены.")
                    else:
                        await query.message.bot.send_message(chat_id, text="Ошибка при получении конфигурации.")
                else:
                    await query.message.bot.send_message(chat_id, text="Не удалось найти созданного клиента.")
                    logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов на сервере {server}.")

                await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} на сервер {server} был одобрен.")

                await state.set_state(BuyProcess.Start)
                set_user_state(chat_id, BuyProcess.Start)

                keyboard_builder = ReplyKeyboardBuilder()
                keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
                keyboard_builder.add(types.KeyboardButton(text="Купить 'США'"))
                keyboard = keyboard_builder.as_markup(resize_keyboard=True)

                await query.message.bot.send_message(chat_id, text="Вы можете снова выбрать действие.",
                                                     reply_markup=keyboard)

            else:
                await query.message.bot.send_message(chat_id, text="Не удалось аутентифицироваться в WireGuard API.")

        else:
            await query.message.edit_caption(caption="Ошибка: Пользователь уже имеет оплаченный статус.")

    elif action == "reject":
        await query.message.bot.send_message(chat_id, text="Ошибка. Ваши данные были отклонены. Если что-то не так, свяжитесь по почте lerk@joulerk.ru")
        await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} на сервер {server} был отклонён.")

        await state.set_state(BuyProcess.Start)
        set_user_state(chat_id, BuyProcess.Start)

        keyboard_builder = ReplyKeyboardBuilder()
        keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
        keyboard_builder.add(types.KeyboardButton(text="Купить 'США'"))
        keyboard = keyboard_builder.as_markup(resize_keyboard=True)

        await query.message.bot.send_message(chat_id, text="Вы можете снова выбрать действие.", reply_markup=keyboard)
