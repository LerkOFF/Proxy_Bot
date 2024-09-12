from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder  # Импортируем конструктор клавиатуры
from config import Config
from states import BuyProcess
from db import add_user
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    logger.info(f"Command 'start' used by user with chat_id: {chat_id}")

    add_user(chat_id)

    # Используем ReplyKeyboardBuilder для создания клавиатуры
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
        "Привет! Я бот для покупки прокси через WireGuard! Выберите действие:",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Start)

async def buy_finland(message: types.Message, state: FSMContext):
    chat_id = message.chat.id

    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Отмена"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
        "Хороший выбор! Переведите ровно 200р на Boosty: https://boosty.to/lerk/donate.\n"
        "После перевода отправьте чек или скриншот подтверждающий это.",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Buying)

async def cancel(message: types.Message, state: FSMContext):
    chat_id = message.chat.id

    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
    keyboard = keyboard_builder.as_markup(resize_keyboard=True)

    await message.answer(
        "Отмена произведена. Вы можете выбрать действие снова.",
        reply_markup=keyboard
    )
    await state.set_state(BuyProcess.Start)

async def handle_file_upload(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    owner_id = Config.TELEGRAM_ID

    inline_keyboard_builder = InlineKeyboardBuilder()
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_{chat_id}"))
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{chat_id}"))
    inline_reply_markup = inline_keyboard_builder.as_markup()

    if message.photo:
        await message.bot.send_photo(owner_id, photo=message.photo[-1].file_id,
                                     caption=f"Чек от пользователя {chat_id}", reply_markup=inline_reply_markup)
    elif message.document:
        await message.bot.send_document(owner_id, document=message.document.file_id,
                                        caption=f"Чек от пользователя {chat_id}", reply_markup=inline_reply_markup)

    await message.answer("Спасибо за отправку подтверждения! Мы скоро свяжемся с вами.")
    logger.info(f"Пользователь с chat_id {chat_id} отправил чек.")

    await state.set_state(BuyProcess.WaitingPaymentConfirmation)
