# buy.py
from datetime import datetime

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import Config
from states import BuyProcess
from db import add_user, set_user_state, get_user_state, is_payment_recent, get_last_payment_date, user_already_has_subscription, update_user_payment
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")

    saved_state = get_user_state(chat_id)
    if saved_state:
        await state.set_state(saved_state)

    add_user(chat_id)

    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
    keyboard_builder.add(types.KeyboardButton(text="Купить 'США'"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
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
        await message.answer("Неизвестная команда.")
        return

    if user_already_has_subscription(chat_id, server):
        await message.answer(f"У вас уже есть активная подписка на сервер {server}.")
        return

    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Отмена"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
        f"Хороший выбор! Переведите ровно 200р на Boosty: https://boosty.to/lerk/donate.\n"
        "После перевода отправьте чек или скриншот подтверждающий это.",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Buying)
    set_user_state(chat_id, BuyProcess.Buying)
    # Сохраняем выбранный сервер в FSMContext
    await state.update_data(server=server, server_ip=server_ip)

async def cancel(message: types.Message, state: FSMContext):
    chat_id = message.chat.id

    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
    keyboard_builder.add(types.KeyboardButton(text="Купить 'США'"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
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

    inline_keyboard_builder = InlineKeyboardBuilder()
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_{chat_id}_{server}"))
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{chat_id}_{server}"))
    inline_reply_markup = inline_keyboard_builder.as_markup()

    if message.photo:
        await message.bot.send_photo(owner_id, photo=message.photo[-1].file_id,
                                     caption=f"Чек от пользователя {chat_id} на сервер {server}", reply_markup=inline_reply_markup)
    elif message.document:
        await message.bot.send_document(owner_id, document=message.document.file_id,
                                        caption=f"Чек от пользователя {chat_id} на сервер {server}", reply_markup=inline_reply_markup)

    await message.answer("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
    logger.info(f"Пользователь с chat_id {chat_id} отправил чек для сервера {server}.")

    await state.set_state(BuyProcess.WaitingPaymentConfirmation)
