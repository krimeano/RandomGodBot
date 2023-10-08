from datetime import datetime
from time import strptime

import telebot.types

from app import bot
from config import TIME_FORMAT
from middleware import keyboard
from tool import get_vocabulary


def send_with_back(chat_id: int | str, text: str):
    bot.send_message(chat_id, text, reply_markup=keyboard.back_button(chat_id))


def send_with_back_to_menu(chat_id: int | str, text: str) -> telebot.types.Message:
    return bot.send_message(chat_id, text, reply_markup=keyboard.back_in_menu_button(chat_id))


def send_welcome(chat_id: int | str):
    bot.send_message(chat_id, get_vocabulary(chat_id)['welcome_text'], reply_markup=keyboard.get_menu_keyboard(chat_id))


def send_temporary(chat_id: int | str, text: str, timeout=15):
    new_message = bot.send_message(chat_id, text)
    bot.delete_message(chat_id, new_message.id, timeout=timeout)


def is_integer(text: str) -> bool:
    try:
        int(text)
        return True
    except Exception:
        return False


def is_int_gt_one(text: str) -> bool:
    try:
        return int(text) >= 1
    except Exception:
        return False


def is_valid_date_format(text: str, f=TIME_FORMAT) -> bool:
    try:
        strptime(text, f)
        return True
    except Exception:
        return False


def is_time_less_or_equal(txt_time_left: str, txt_time_right='') -> bool:
    if not txt_time_right:
        txt_time_right = get_time_now()

    return strptime(txt_time_left, TIME_FORMAT) <= strptime(txt_time_right, TIME_FORMAT)


def get_time_now() -> str:
    return datetime.now().strftime(TIME_FORMAT)


def display_name(username: str, first_name='', last_name='') -> str:
    full_name = []
    if first_name:
        full_name.append(first_name)
    if last_name:
        full_name.append(last_name)
    if not full_name:
        full_name.append(username_normal(username))

    return ' '.join(full_name)


def username_normal(username='') -> str:
    prefix = ''
    if username and username[0] != '@':
        prefix = '@'
    return prefix + username
