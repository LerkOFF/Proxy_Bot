import qrcode
import os
from aiogram import types
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from db import get_user_by_chat_id, update_user_payment, set_user_state
from wg import WgEasyAPI
from config import Config
from states import BuyProcess  # Импортируем BuyProcess
import logging

logger = logging.getLogger(__name__)
wg_api = WgEasyAPI(base_url="http://wg.oai.su:51821", password=Config.WG_PASSWORD)

qr_code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qrcodes')

if not os.path.exists(qr_code_dir):
    os.makedirs(qr_code_dir)


async def handle_approval(query: types.CallbackQuery, state: FSMContext):
    action, chat_id = query.data.split('_')

    if action == "approve":
        user = get_user_by_chat_id(chat_id)
        if user and not user["date_start"]:
            update_user_payment(chat_id)
            wg_api.authenticate()

            creation_response = wg_api.create_client(chat_id)
            logger.info(f"Ответ от WireGuard API при создании клиента: {creation_response}")

            clients = wg_api.get_clients()
            created_client = next((client for client in clients if client['name'] == str(chat_id)), None)

            if created_client:
                client_id = created_client['id']
                client_config = wg_api.get_config_client(client_id)

                if client_config:
                    img = qrcode.make(client_config)
                    qr_code_path = os.path.join(qr_code_dir, f"wg_qrcode_{chat_id}.png")

                    img.save(qr_code_path)

                    qr_code_input = FSInputFile(qr_code_path)
                    await query.message.bot.send_photo(chat_id, qr_code_input,
                                                       caption="Успешно! Вот ваш QR-код для подключения WireGuard.")

                    await query.message.bot.send_message(chat_id,
                                                         text=f"Вот ваша конфигурация WireGuard:\n\n{client_config}")
                    logger.info(f"Клиент с chat_id {chat_id} одобрен, и QR-код с конфигурацией отправлены.")
                else:
                    await query.message.bot.send_message(chat_id, text="Ошибка при получении конфигурации.")
            else:
                await query.message.bot.send_message(chat_id, text="Не удалось найти созданного клиента.")
                logger.error(f"Клиент с chat_id {chat_id} не найден среди списка клиентов.")
            await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} был одобрен.")

            await state.set_state(BuyProcess.Start)
            set_user_state(chat_id, BuyProcess.Start)

            keyboard_builder = ReplyKeyboardBuilder()
            keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
            keyboard = keyboard_builder.as_markup(resize_keyboard=True)

            await query.message.bot.send_message(chat_id, text="Вы можете снова выбрать действие.",
                                                 reply_markup=keyboard)

        else:
            await query.message.edit_caption(caption="Ошибка: Пользователь уже имеет оплаченный статус.")

    elif action == "reject":
        await query.message.bot.send_message(chat_id, text="Ошибка. Ваши данные были отклонены.")
        await query.message.edit_caption(caption=f"Платёж пользователя {chat_id} был отклонён.")

        await state.set_state(BuyProcess.Start)
        set_user_state(chat_id, BuyProcess.Start)

        keyboard_builder = ReplyKeyboardBuilder()
        keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
        keyboard = keyboard_builder.as_markup(resize_keyboard=True)

        await query.message.bot.send_message(chat_id, text="Вы можете снова выбрать действие.", reply_markup=keyboard)
