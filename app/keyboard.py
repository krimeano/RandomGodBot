import telebot

from tool import get_vocabulary


def get_menu_keyboard(user_id):
    buttons = get_vocabulary(user_id)['menu_buttons']
    menu_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_keyboard.row(buttons['create_draw'], buttons['my_draws'])
    menu_keyboard.row(buttons['my_channels'], buttons['toggle_language'])
    return menu_keyboard


def get_draw_keyboard(user_id):
    buttons = get_vocabulary(user_id)['draw']['draw_buttons']
    draw_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    draw_keyboard.row(buttons[5])
    draw_keyboard.row(buttons[6], buttons[7])
    return draw_keyboard


def back_button(user_id):
    back_buttons = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_buttons.row(get_vocabulary(user_id)['draw']['back'])
    return back_buttons


def back_in_menu_button(user_id):
    buttons = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.row(get_vocabulary(user_id)['back_in_menu'])
    return buttons


def my_channels_buttons(user_id):
    voc = get_vocabulary(user_id)
    buttons = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons.row(voc['my_channels']['add_new'], voc['my_channels']['delete'])
    buttons.row(voc['back_in_menu'])
    return buttons
