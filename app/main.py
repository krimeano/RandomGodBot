import time
from datetime import datetime

import telebot.types

import bot_lib
import middleware
import models
from app import fsm, bot
from app import main_base as base
from config import password, TIME_FORMAT
from middleware import keyboard
from tool import language_check, create_inline_keyboard, get_vocabulary

middleware.start_draw_timer()


# middleware.end_draw_timer() // @todo


# -------------------------------------- # START # -------------------------------------- #
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    base.delete(models.State, user_id=user_id)

    if message.chat.type == 'private':
        stored, _ = language_check(user_id)

        if not stored:
            base.new(models.User, str(user_id), str(message.chat.username), "RU")

        bot_lib.send_welcome(user_id)


@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'geton')
def get_on_draw(call):
    try:
        user_id = call.message.chat.id
        text = get_vocabulary(user_id)['draw']
        tmp = middleware.new_player(call)

        if tmp[1] == 'not_subscribed':
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text=text['not_subscribe'])
        if not tmp[0]:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text=text['already_in'])
        else:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text=text['got_on'])
            bot.edit_message_reply_markup(chat_id=user_id, message_id=call.message.message_id, inline_message_id=call.inline_message_id,
                                          reply_markup=create_inline_keyboard({f"({tmp[1]}) {tmp[2]}": call.data}))

    except Exception as exception:
        print('EXCEPT', 'get_on_draw', str(exception))
        pass


# language checkers
# -------------------------------------- # change language # -------------------------------------- #
@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['menu_buttons']['toggle_language'])
def change_language(message):
    user_id = message.chat.id
    user = base.get_one(models.User, user_id=str(user_id))

    new_language = 'RU'

    if user.language == 'RU':
        new_language = 'EN'

    base.update(models.User, {'language': new_language}, user_id=str(user_id))

    bot_lib.send_welcome(user_id)


# -------------------------------------- # back in main menu # -------------------------------------- #
@bot.callback_query_handler(func=lambda call: call.data == 'close')
def handle_close(call: telebot.types.CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    back_in_menu(call.message)


@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['back_in_menu'])
def back_in_menu(message):
    user_id = message.chat.id
    base.delete(models.State, user_id=str(user_id))

    progress_draw = base.get_one(models.Draw, user_id=str(user_id), status='progress')
    if progress_draw:
        base.delete(models.Draw, id=progress_draw.id)
        base.delete(models.DrawPrize, draw_id=progress_draw.id)

    base.delete(models.SubscribeChannel, user_id=str(user_id))

    bot_lib.send_welcome(user_id)


# -------------------------------------- # back in draw menu # -------------------------------------- #
@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['draw']['back'] and middleware.check_post(message.chat.id))
def back_in_draw_menu(message):
    user_id = message.chat.id
    base.delete(models.State, user_id=str(user_id))
    middleware.send_draw_info(user_id)


# -------------------------------------- # back in draw menu # -------------------------------------- #
@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['menu_buttons']['my_draws'])
def my_draws(message):
    user_id = message.chat.id
    middleware.my_draw_info(user_id)
    fsm.set_state(user_id, 'my_draws', number=0)


@bot.callback_query_handler(func=lambda call: call.data == 'next')
def handle_next(call):
    handle_move(call)


@bot.callback_query_handler(func=lambda call: call.data == 'back')
def handle_back(call):
    handle_move(call, -1)


def handle_move(call, step=1):
    user_id = call.message.chat.id
    try:
        text = get_vocabulary(user_id)['my_draw']
        row = int(fsm.get_state_arg(user_id)['number']) + step
        tmp = middleware.my_draw_info(user_id, row=row)

        if tmp == 'first':
            bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text=text['first'])
            return

        if tmp == 'last':
            bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text=text['last'])
            return

        bot.delete_message(user_id, call.message.message_id)
        fsm.set_state(user_id, 'my_draws', number=row)
    except Exception as exception:
        print('EXCEPT', 'handle_move', step, str(exception))
        fsm.remove_state(user_id)
        bot.delete_message(user_id, call.message.message_id)


############################################ draw func #################################################
# -------------------------------------- # submit # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][6])
def submit(message):
    user_id = message.chat.id
    text = language_check(user_id)
    bot.send_message(user_id, text[1]['draw']['submit_text'], reply_markup=keyboard.get_menu_keyboard(user_id))
    base.update(models.Draw, {'status': 'not_posted'}, user_id=str(user_id), status='progress')
    base.delete(models.State, user_id=str(user_id))


@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['menu_buttons']['create_draw'])
def ask_password_before_new_raffle(message: telebot.types.Message):
    ask_password(message, 'new_raffle')


@bot.message_handler(func=lambda message: message.text == get_vocabulary(message.chat.id)['menu_buttons']['my_channels'])
def ask_password_before_my_channels(message: telebot.types.Message):
    ask_password(message, 'my_channels')


def ask_password(message: telebot.types.Message, set_state: str):
    user_id = message.chat.id
    if not password:
        fsm.set_state(user_id, set_state)
        proceed_to_state(message, set_state)
    else:
        ask_message = bot_lib.send_with_back_to_menu(user_id, "Для продолжения введите пароль:")  # @todo l10n
        fsm.set_state(user_id, '.'.join(["ask_password", set_state]), ask_message_id=ask_message.id)


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id).startswith('ask_password.'))
def handle_password(message: telebot.types.Message):
    user_id = message.chat.id
    bot.delete_message(user_id, message.id)

    tmp = fsm.get_state_arg(user_id)

    if 'ask_message_id' in tmp:
        bot.delete_message(user_id, tmp['ask_message_id'])

    if message.text != password:
        bot_lib.send_temporary(user_id, 'Пароль неверен')
        back_in_menu(message)
        return

    state = fsm.get_state_key(user_id).split('.').pop()

    fsm.set_state(user_id, state)

    bot_lib.send_temporary(user_id, 'Пароль введен правильно')

    proceed_to_state(message, state)


def proceed_to_state(message: telebot.types.Message, state: str):
    if state == 'new_raffle':
        return enter_id(message)

    if state == 'my_channels':
        return my_channels(message)

    print('unknown new state', state)
    back_in_menu(message)


# -------------------------------------- # enter_id # -------------------------------------- #
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'new_raffle')
def enter_id(message):
    user_id = message.chat.id

    progress_draw = base.get_one(models.Draw, user_id=str(user_id), status='progress')
    if progress_draw:
        base.delete(models.Draw, id=progress_draw.id)
        base.delete(models.DrawPrize, draw_id=progress_draw.id)

    base.delete(models.SubscribeChannel, user_id=str(user_id))

    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, "writing_channel_id")

    buttons = middleware.render_choose_my_channel_inline_keyboard(user_id)
    bot.send_message(user_id, text['choose_chanel_id'], reply_markup=buttons)


@bot.callback_query_handler(func=lambda call: call.data.startswith('new_raffle.choose_my_channel.'))
def enter_text(call: telebot.types.CallbackQuery):
    user_id = call.message.chat.id
    record_id = int(call.data.split("new_raffle.choose_my_channel.").pop())
    channel: models.MyChannel = base.get_one(models.MyChannel, id=record_id, user_id=user_id)

    if not channel:
        bot.send_message(user_id, 'CHANNEL NOT FOUND!')
        return back_in_menu(call.message)

    bot.delete_message(user_id, call.message.id)

    text = get_vocabulary(user_id)['draw']
    bot.send_message(user_id, 'Выбран канал {0} "{1}"'.format(channel.chanel_id, channel.chanel_name))
    fsm.set_state(user_id, "writing_text", chanel_id=channel.chanel_id, chanel_name=channel.chanel_name)
    bot_lib.send_with_back_to_menu(user_id, text['draw_text'])


# -------------------------------------- # enter_text # -------------------------------------- #
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'writing_channel_id')
def enter_text_deprecated(message):
    status = ['creator', 'administrator']
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']

    try:
        if str(bot.get_chat_member(chat_id=message.text, user_id=message.from_user.id).status) not in status:
            bot_lib.send_with_back_to_menu(user_id, text['not_admin'])
            return ''

        tmp = bot.send_message(message.text, 'test')
        bot.delete_message(tmp.chat.id, tmp.message_id)
    except Exception as exception:
        print('EXCEPT', 'enter_text', str(exception))
        bot_lib.send_with_back_to_menu(user_id, text['not_in_chanel'])
        return ''
    fsm.set_state(user_id, "writing_text", chanel_id=message.text, chanel_name=tmp.chat.title)
    bot_lib.send_with_back_to_menu(user_id, text['draw_text'])


# -------------------------------------- # writing_text # -------------------------------------- #
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'writing_text')
def enter_photo(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    tmp = fsm.get_state_arg(user_id)
    fsm.set_state(user_id, "enter_photo", **tmp, draw_text=message.text)

    bot_lib.send_with_back_to_menu(user_id, text['file'])


# -------------------------------------- # enter_photo # -------------------------------------- #
@bot.message_handler(content_types=['text', 'photo', 'document'], func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_photo')
def enter_photo(message):
    file_id = ''
    file_type = 'text'

    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']

    tmp = fsm.get_state_arg(user_id)
    if message.content_type == 'photo':
        file_id = message.photo[0].file_id
        file_type = 'photo'
    elif message.content_type == 'document':
        file_id = message.document.file_id
        file_type = 'document'

    fsm.set_state(user_id, "enter_prize_kinds", **tmp, file_type=file_type, file_id=file_id)
    bot_lib.send_with_back_to_menu(user_id, text['prize_kinds'])


# PRIZE KINDS
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_prize_kinds')
def handle_prize_kinds(message: telebot.types.Message):
    user_id = message.chat.id
    text = get_vocabulary(message.chat.id)['draw']

    if not bot_lib.is_int_gt_one(message.text):
        bot.send_message(user_id, text['at_least_one'])
        return
    prize_kinds = int(message.text)
    tmp = fsm.get_state_arg(user_id)
    current_kind_ix = 0
    prizes = []

    for _ in range(prize_kinds):
        prizes.append([0, '', False, []])

    fsm.set_state(user_id, "enter_prize_kind_winners_count", **tmp, prizes=prizes, current_kind_ix=current_kind_ix)
    bot_lib.send_with_back_to_menu(user_id, text['prize_kind_winners_count'].format(current_kind_ix + 1))


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_prize_kind_winners_count')
def handle_prize_kind_winners_count(message: telebot.types.Message):
    user_id = message.chat.id
    text = get_vocabulary(message.chat.id)['draw']

    if not bot_lib.is_int_gt_one(message.text):
        bot.send_message(user_id, text['at_least_one'])
        return

    tmp = fsm.get_state_arg(user_id)
    current_kind_ix = tmp['current_kind_ix']
    tmp['prizes'][current_kind_ix][0] = int(message.text)
    print('tmp = ', tmp)
    fsm.set_state(user_id, "enter_prize_kind_winners_text", **tmp)

    bot_lib.send_with_back_to_menu(user_id, text['prize_kind_winners_text'].format(current_kind_ix + 1))


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_prize_kind_winners_text')
def handle_prize_kind_winners_text(message: telebot.types.Message):
    user_id = message.chat.id
    text = get_vocabulary(message.chat.id)['draw']

    tmp = fsm.get_state_arg(user_id)
    current_kind_ix = tmp['current_kind_ix']
    tmp['prizes'][current_kind_ix][1] = message.text
    print('tmp = ', tmp)
    fsm.set_state(user_id, "select_prize_winners_is_random", **tmp)

    buttons = middleware.render_is_random_inline_keyboard(user_id)
    bot.send_message(message.chat.id, text['prize_kind_winners_is_random'].format(current_kind_ix + 1), reply_markup=buttons)


@bot.callback_query_handler(func=lambda call: call.data.startswith('new_raffle.is_random.'))
def handle_prize_kind_winners_is_random(call: telebot.types.CallbackQuery):
    user_id = call.message.chat.id
    bot.delete_message(user_id, call.message.id)

    text = get_vocabulary(user_id)['draw']

    tmp = fsm.get_state_arg(user_id)

    current_kind_ix = tmp['current_kind_ix']
    is_random = call.data.split('.').pop() == 'yes'
    tmp['prizes'][current_kind_ix][2] = is_random

    if not is_random:
        fsm.set_state(user_id, "enter_prize_kind_winners_manual", **tmp)
        bot_lib.send_with_back_to_menu(user_id, text['prize_kind_winners_manual'].format(current_kind_ix + 1, tmp['prizes'][current_kind_ix][0], 1))
    else:
        increment_current_kind_ix(user_id, tmp)


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_prize_kind_winners_manual')
def handle_prize_kind_winners_manual(message: telebot.types.Message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    tmp = fsm.get_state_arg(user_id)
    current_kind_ix = tmp['current_kind_ix']
    winners: list[str] = tmp['prizes'][current_kind_ix][3]
    winner = message.text.strip()  # @todo проверить что пользователь существует и в чате
    if winner not in winners:
        winners.append(winner)

    if len(winners) < tmp['prizes'][current_kind_ix][0]:
        fsm.set_state(user_id, "enter_prize_kind_winners_manual", **tmp)
        bot_lib.send_with_back_to_menu(user_id, text['prize_kind_winners_manual'].format(current_kind_ix + 1, tmp['prizes'][current_kind_ix][0], len(winners) + 1))
    else:
        increment_current_kind_ix(user_id, tmp)


def increment_current_kind_ix(user_id, current_state):
    text = get_vocabulary(user_id)['draw']
    current_kind_ix = current_state['current_kind_ix']
    current_kind_ix += 1
    current_state['current_kind_ix'] = current_kind_ix
    print('tmp = ', current_state)

    if current_kind_ix < len(current_state['prizes']):
        fsm.set_state(user_id, "enter_prize_kind_winners_count", **current_state)
        bot_lib.send_with_back_to_menu(user_id, text['prize_kind_winners_count'].format(current_kind_ix + 1))
    else:
        fsm.set_state(user_id, "enter_start_time", **current_state)
        bot_lib.send_with_back_to_menu(user_id, text['post_time'].format(bot_lib.get_time_now()))


# -------------------------------------- # enter_start_time # -------------------------------------- #
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_start_time')
def enter_start_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']

    if not bot_lib.is_valid_date_format(message.text):
        bot.send_message(user_id, text['invalid_format_time'].format(bot_lib.get_time_now()))
        return

    if bot_lib.is_time_less_or_equal(message.text):
        bot.send_message(user_id, text['over_time'])
        return

    tmp = fsm.get_state_arg(user_id)
    fsm.set_state(user_id, "enter_end_time", **tmp, start_time=message.text)

    bot_lib.send_with_back_to_menu(user_id, text['end_time'].format(bot_lib.get_time_now()))


# -------------------------------------- # enter_end_time # -------------------------------------- #
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_end_time')
def enter_end_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']

    if not bot_lib.is_valid_date_format(message.text):
        bot.send_message(user_id, text['invalid_format_time'].format(bot_lib.get_time_now()))
        return

    if bot_lib.is_time_less_or_equal(message.text):
        bot.send_message(user_id, text['over_time'])
        return

    tmp = fsm.get_state_arg(user_id)

    if bot_lib.is_time_less_or_equal(message.text, tmp['start_time']):
        bot.send_message(user_id, text['post_bigger'].format(bot_lib.get_time_now()))
        return

    fsm.set_state(user_id, "enter_restricted_days", **tmp, end_time=message.text)

    bot_lib.send_with_back_to_menu(user_id, 'Введите за сколько дней до подведения итогов запретить участие, 0 если нет ограничения.')


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'enter_restricted_days')
def enter_restricted_days(message):
    user_id = message.chat.id
    text = get_vocabulary(message.chat.id)['draw']

    if not bot_lib.is_integer(message.text):
        bot.send_message(user_id, 'Введите число')
        return

    restricted_days = int(message.text)

    if restricted_days < 0:
        bot.send_message(user_id, 'Должно быть неотрицательное число')
        return

    tmp = fsm.get_state_arg(user_id)

    fsm.set_state(user_id, "enter_restricted_days", **tmp, restricted_days=restricted_days)

    tmp = fsm.get_state_arg(user_id)

    if tmp['file_type'] == 'photo':
        bot.send_photo(user_id, tmp['file_id'], middleware.create_draw_progress(user_id, tmp), reply_markup=keyboard.get_draw_keyboard(user_id))

    elif tmp['file_type'] == 'document':
        bot.send_document(user_id, tmp['file_id'], caption=middleware.create_draw_progress(user_id, tmp), reply_markup=keyboard.get_draw_keyboard(user_id))
    else:
        bot.send_message(user_id, middleware.create_draw_progress(user_id, tmp), reply_markup=keyboard.get_draw_keyboard(user_id))


# -------------------------------------- # change start time # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][0])
def change_start_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, 'change_post_time')
    bot_lib.send_with_back(user_id, text['post_time'].format(bot_lib.get_time_now()))


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'change_post_time')
def confirm_change_start_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']

    if not bot_lib.is_valid_date_format(message.text):
        bot.send_message(user_id, text['invalid_format_time'].format(bot_lib.get_time_now()))
        return

    if time.strptime(datetime.now().strftime(TIME_FORMAT), TIME_FORMAT) >= time.strptime(message.text, TIME_FORMAT):
        bot.send_message(user_id, text['over_time'])
        return

    tmp = base.get_one(models.Draw, user_id=str(user_id), status='progress')

    if time.strptime(message.text, TIME_FORMAT) >= time.strptime(tmp.end_time, TIME_FORMAT):
        bot.send_message(user_id, text['post_bigger'].format(bot_lib.get_time_now()))
        return

    base.update(models.Draw, {'post_time': message.text}, user_id=str(user_id), status='progress')
    middleware.send_draw_info(user_id)


# -------------------------------------- # change end time # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][1])
def change_end_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, 'change_end_time')
    bot_lib.send_with_back(user_id, text['end_time'].format(bot_lib.get_time_now()))


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'change_end_time')
def confirm_change_end_time(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    try:
        print(time.strptime(message.text, TIME_FORMAT))
    except Exception as exception:
        print('EXCEPT', 'confirm_change_end_time', str(exception))
        bot.send_message(user_id, text['invalid_format_time'].format(bot_lib.get_time_now()))
        return

    if time.strptime(datetime.now().strftime(TIME_FORMAT), TIME_FORMAT) >= time.strptime(message.text, TIME_FORMAT):
        bot.send_message(user_id, text['over_time'])
        return

    tmp = base.get_one(models.Draw, user_id=str(user_id), status='progress')
    if time.strptime(message.text, TIME_FORMAT) <= time.strptime(tmp.post_time, TIME_FORMAT):
        bot.send_message(user_id, text['post_bigger'].format(bot_lib.get_time_now()))
        return

    base.update(models.Draw, {'end_time': message.text}, user_id=str(user_id), status='progress')
    middleware.send_draw_info(user_id)


# -------------------------------------- # change text # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][3])
def change_text(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, 'change_draw_text')
    bot_lib.send_with_back(user_id, text['draw_text'])


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'change_draw_text')
def confirm_change_draw_text(message):
    user_id = message.chat.id
    base.update(models.Draw, {'text': message.text}, user_id=str(user_id), status='progress')
    middleware.send_draw_info(user_id)


# -------------------------------------- # change photo # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][4])
def change_photo(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, 'change_draw_photo')
    bot_lib.send_with_back(user_id, text['file'])


@bot.message_handler(content_types=['text', 'photo', 'document'], func=lambda message: fsm.get_state_key(message.chat.id) == 'change_draw_photo')
def confirm_change_draw_photo(message):
    file_id = ''
    file_type = 'text'
    if message.content_type == 'photo':
        file_id = message.photo[0].file_id
        file_type = 'photo'
    elif message.content_type == 'document':
        file_id = message.document.file_id
        file_type = 'document'

    user_id = message.chat.id
    base.update(models.Draw, {'file_id': file_id, 'file_type': file_type}, user_id=str(user_id), status='progress')
    middleware.send_draw_info(user_id)


# -------------------------------------- # add channel check # -------------------------------------- #
@bot.message_handler(func=lambda message: middleware.check_post(message.chat.id) and message.text == get_vocabulary(message.chat.id)['draw']['draw_buttons'][5])
def add_chanel(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    fsm.set_state(user_id, 'add_check_channel')
    bot_lib.send_with_back(user_id, text['chanel_id_check'])


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'add_check_channel')
def add_check_channel(message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['draw']
    try:
        status = ['creator', 'administrator']
        if str(bot.get_chat_member(chat_id=message.text, user_id=message.from_user.id).status) not in status:
            bot.send_message(text['not_admin'])
            return ''
    except Exception as exception:
        print('EXCEPT', 'add_check_channel', str(exception))
        bot.send_message(user_id, text['not_in_chanel'])
        return ''
    tmp = base.get_one(models.Draw, user_id=str(user_id), status='progress')
    base.new(models.SubscribeChannel, tmp.id, str(user_id), message.text)
    middleware.send_draw_info(user_id)
    print(base.select_all(models.SubscribeChannel))


######## My Channels
@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'my_channels')
def my_channels(message: telebot.types.Message):
    user_id = message.chat.id
    text = get_vocabulary(user_id)['menu_buttons']['my_channels']
    buttons = middleware.render_my_channels_inline_keyboard(user_id)
    bot.send_message(user_id, text, reply_markup=buttons)


@bot.callback_query_handler(func=lambda call: call.data == 'my_channels.add_new')
def handle_my_channels_add_new(call: telebot.types.CallbackQuery):
    user_id = call.message.chat.id
    fsm.set_state(user_id, 'my_channels.add_new')
    bot.delete_message(user_id, call.message.message_id)
    bot_lib.send_with_back_to_menu(user_id, get_vocabulary(user_id)['draw']['chanel_id'])


@bot.message_handler(func=lambda message: fsm.get_state_key(message.chat.id) == 'my_channels.add_new')
def handle_my_channels_add_new_entered(message: telebot.types.Message):
    user_id = message.chat.id
    try:
        chat = bot.get_chat(message.text)
        base.new(models.MyChannel, user_id, message.text, chat.title)
        fsm.set_state(user_id, 'my_channels')
        bot.send_message(user_id, 'Канал добавлен!')
        my_channels(message)
    except Exception as exception:
        print('EXCEPT', 'handle_my_channels_add_new_entered', str(exception))
        bot_lib.send_with_back_to_menu(user_id, 'Не могу получить данные канала')


@bot.callback_query_handler(func=lambda call: call.data.startswith('my_channels.view.'))
def handle_my_channels_view(call: telebot.types.CallbackQuery):
    record_id = int(call.data.split('.').pop())
    my_channel = base.get_one(models.MyChannel, id=record_id)
    user_id = call.message.chat.id
    bot.delete_message(user_id, call.message.message_id)
    text = 'Канал "{0}"\n id: {1}'.format(my_channel.chanel_name, my_channel.chanel_id)
    bot_lib.send_with_back_to_menu(user_id, text)


@bot.callback_query_handler(func=lambda call: call.data.startswith('my_channels.delete.'))
def handle_my_channels_delete(call: telebot.types.CallbackQuery):
    record_id = int(call.data.split('.').pop())
    base.delete(models.MyChannel, id=record_id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, 'Канал удален', False)
    my_channels(call.message)


if __name__ == '__main__':
    bot.polling(none_stop=True)
