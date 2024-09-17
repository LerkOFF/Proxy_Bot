# buy.py
from datetime import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import Config
from states import BuyProcess
from db import add_user, set_user_state, user_already_has_subscription, update_user_payment, get_user_state
from keyboards import get_main_menu_keyboard, get_cancel_keyboard
from utils import safe_send_message
from logger import logger

async def start(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")

    saved_state = get_user_state(chat_id)
    if saved_state:
        await state.set_state(saved_state)

    add_user(chat_id)

    keyboard = get_main_menu_keyboard()

    await safe_send_message(
        message.bot,
        chat_id,
        "Привет! Я бот для покупки прокси через WireGuard! Выберите действие:",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Start)
    set_user_state(chat_id, BuyProcess.Start)

async def buy_server(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    text = message.text

    if text == "Купить 'Финляндия'":
        server = 'Finland'
        server_ip = Config.WG1_SERVER_IP
    elif text == "Купить 'США'":
        server = 'USA'
        server_ip = Config.WG2_SERVER_IP
    else:
        await safe_send_message(message.bot, chat_id, "Неизвестная команда.")
        return

    if user_already_has_subscription(chat_id, server):
        await safe_send_message(message.bot, chat_id, f"У вас уже есть активная подписка на сервер {server}.")
        return

    keyboard = get_cancel_keyboard()

    await safe_send_message(
        message.bot,
        chat_id,
        f"Хороший выбор! Переведите ровно 200р на Boosty: https://boosty.to/lerk/donate.\n"
        "После перевода отправьте чек или скриншот подтверждающий это.",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Buying)
    set_user_state(chat_id, BuyProcess.Buying)
    # Сохраняем выбранный сервер в FSMContext
    await state.update_data(server=server, server_ip=server_ip)
    logger.info(f"Пользователь {chat_id} выбрал сервер {server}")

async def cancel(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    logger.info(f"Пользователь {chat_id} отменил процесс покупки")

    keyboard = get_main_menu_keyboard()

    await safe_send_message(
        message.bot,
        chat_id,
        "Отмена произведена. Вы можете выбрать действие снова.",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Start)
    set_user_state(chat_id, BuyProcess.Start)

async def handle_file_upload(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    owner_id = Config.TELEGRAM_ID

    data = await state.get_data()
    server = data.get('server')
    server_ip = data.get('server_ip')

    from keyboards import get_approval_inline_keyboard
    inline_reply_markup = get_approval_inline_keyboard(chat_id, server)

    if message.photo:
        await message.bot.send_photo(
            owner_id,
            photo=message.photo[-1].file_id,
            caption=f"Чек от пользователя {chat_id} на сервер {server}",
            reply_markup=inline_reply_markup
        )
    elif message.document:
        await message.bot.send_document(
            owner_id,
            document=message.document.file_id,
            caption=f"Чек от пользователя {chat_id} на сервер {server}",
            reply_markup=inline_reply_markup
        )

    await safe_send_message(
        message.bot,
        chat_id,
        "Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    logger.info(f"Пользователь с chat_id {chat_id} отправил чек для сервера {server}.")

    await state.set_state(BuyProcess.WaitingPaymentConfirmation)
    set_user_state(chat_id, BuyProcess.WaitingPaymentConfirmation)
