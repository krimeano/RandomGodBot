from time import strptime

from app import bot
from middleware import keyboard
from tool import language_check


def send_with_back(chat_id: int | str, text: str):
    bot.send_message(chat_id, text, reply_markup=keyboard.back_button(chat_id))


def send_with_back_to_menu(chat_id: int | str, text: str):
    bot.send_message(chat_id, text, reply_markup=keyboard.back_in_menu_button(chat_id))


def send_welcome(chat_id: int | str):
    bot.send_message(chat_id, language_check(chat_id)[1]['menu']['welcome_text'], reply_markup=keyboard.get_menu_keyboard(chat_id))


def send_temporary(chat_id: int | str, text: str, timeout=15):
    new_message = bot.send_message(chat_id, text)
    bot.delete_message(chat_id, new_message.id, timeout=timeout)


def is_integer(text: str) -> bool:
    try:
        int(text)
        return True
    except Exception:
        return False


def is_valid_date_format(text: str, f='%Y-%m-%d %H:%M') -> bool:
    try:
        strptime(text, f)
        return True
    except Exception:
        return False
