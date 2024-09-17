from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types

def get_main_menu_keyboard():
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Купить 'Финляндия'"))
    keyboard_builder.add(types.KeyboardButton(text="Купить 'США'"))
    return keyboard_builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.add(types.KeyboardButton(text="Отмена"))
    return keyboard_builder.as_markup(resize_keyboard=True)

def get_approval_inline_keyboard(chat_id, server):
    inline_keyboard_builder = InlineKeyboardBuilder()
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_{chat_id}_{server}"))
    inline_keyboard_builder.add(types.InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{chat_id}_{server}"))
    return inline_keyboard_builder.as_markup()
