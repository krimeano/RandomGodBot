import random
import threading
import time

import telebot.types

import bot_lib
import keyboard
import models
from app import middleware_base, bot, post_base, end_base
from tool import language_check, create_inline_keyboard, get_vocabulary


def check_user(user_id) -> models.User | bool:
    user = middleware_base.get_one(models.User, user_id=str(user_id))
    if user is not None:
        return user
    else:
        return False


def create_draw_progress(user_id, tmp) -> models.Draw:
    middleware_base.delete(models.Draw, user_id=str(user_id), status='progress')

    prizes = tmp['prizes']  # [[0, '', False, []]]

    draw = middleware_base.new(
        models.Draw,
        str(user_id), tmp['chanel_id'], tmp['chanel_name'], tmp['draw_text'], tmp['file_type'], tmp['file_id'], tmp['start_time'], tmp['end_time'], tmp['restricted_hours']
    )

    for prize in prizes:
        [winners_count, description, is_manual, preset_winners] = prize
        middleware_base.new(
            models.DrawPrize,
            draw.id, int(winners_count), description, preset_winners
        )

    middleware_base.delete(models.State, user_id=str(user_id))

    return draw


def check_post(user_id) -> models.Draw | None:
    return middleware_base.get_one(models.Draw, user_id=str(user_id), status='progress')


def send_draw_info(user_id):
    draw = check_post(str(user_id))
    draw_text = render_draw_info(draw, 'preview_text')
    send_draw_message(user_id, draw, draw_text, keyboard.get_draw_keyboard(user_id))
    middleware_base.delete(models.State, user_id=user_id)


def my_draw_info(user_id, row=0):
    if row < 0:
        return 'first'

    text = language_check(user_id)[1]['my_draw']

    not_posted: list[models.Draw] = middleware_base.select_all(models.Draw, user_id=str(user_id), status='not_posted')
    posted: list[models.Draw] = middleware_base.select_all(models.Draw, user_id=str(user_id), status='posted')

    all_draws = not_posted + posted

    if len(all_draws) == 0:
        bot.send_message(user_id, text['no_draw'])
        return

    if row >= len(all_draws):
        return 'last'

    draw = all_draws[row]
    draw_text = render_draw_info(draw)
    keyboard_markup = create_inline_keyboard({text['back']: "back", text['next']: "next"}, 2)
    send_draw_message(user_id, draw, draw_text, keyboard_markup)


def render_draw_info(draw: models.Draw, title_key='your_draw') -> str:
    text = language_check(draw.user_id)[1]['my_draw']
    prizes: list[models.DrawPrize] = middleware_base.select_all(models.DrawPrize, draw_id=draw.id)

    draw_text = f"{text[title_key]}\n"
    draw_text += f"{text['post_time_text']} {draw.post_time}\n"
    draw_text += f"{text['over_time_text']} {draw.end_time}\n"

    if draw.restricted_hours:
        draw_text += f"{text['draw_restricted_hours_text']} {draw.restricted_hours}\n"

    draw_text += f"{text['chanel/chat']} {draw.chanel_name}\n"
    draw_text += f"Победители:\n"

    for prize in prizes:
        if prize.preset_winners:
            draw_text += f" - {prize.preset_winners} {prize.description};\n"
        else:
            draw_text += f" - {prize.winners_count} случайных игроков {prize.description};\n"

    draw_text += f"{text['text']} {draw.text}"

    return draw_text


def start_draw_timer():
    def timer():
        while 1:
            for item in post_base.select_all(models.Draw, status='not_posted'):
                if bot_lib.is_time_less_or_equal(item.post_time):
                    try:
                        text = get_vocabulary(item.user_id)['draw']
                        buttons = create_inline_keyboard({text['get_on']: f'geton_{item.id}'})
                        tmz = send_draw_message(item.chanel_id, item, item.text, buttons)
                        post_base.update(models.Draw, {'message_id': tmz.message_id, 'status': 'posted'}, id=item.id)
                    except Exception as exception:
                        print('EXCEPT', 'start_draw_timer timer', str(exception))
                        post_base.update(models.Draw, {'status': 'archived'}, id=item.id)
            time.sleep(55)

    r_t = threading.Thread(target=timer)
    r_t.start()


def end_draw_timer():
    def end_timer():
        while 1:
            for item in end_base.select_all(models.Draw, status='posted'):
                count = 0

                if bot_lib.is_time_less_or_equal(item.end_time):
                    text = language_check(item.user_id)[1]['draw']
                    players = end_base.select_all(models.DrawPlayer, draw_id=str(item.id))

                    if not players:
                        winners = f"{item.text}\n*****\n{text['no_winners']}"
                        owin = f"{text['no_winners']}"

                    else:
                        winners = f"{item.text}\n*****\n{text['winners']}\n"  # @todo winners
                        owin = f"{text['winners']}\n"
                        for x in range(int(item.winners_count)):
                            if count >= len(players):
                                break
                            random_player = random.choice(players)
                            winners += f"<a href='tg://user?id={random_player.user_id}'>{random_player.user_name}</a>\n"
                            owin += f"<a href='tg://user?id={random_player.user_id}'>{random_player.user_name}</a>\n"
                            count += 1
                    try:
                        bot.send_message(chat_id=str(item.chanel_id), text=winners, parse_mode='HTML')

                    except:
                        end_base.update(models.Draw, {'status': 'archived'}, id=item.id)
                        bot.send_message(item.chanel_id, text['failed_post'])
                        return

                    bot.send_message(item.user_id, f"{text['your_draw_over']}\n{owin}", parse_mode='HTML')
                    end_base.update(models.Draw, {'status': 'archived'}, id=item.id)
                    time.sleep(1)

            time.sleep(5)

    r_t = threading.Thread(target=end_timer)
    r_t.start()


get_on_restricted_statuses = ('left', 'kicked', 'restricted', 'administrator', 'creator')
get_on_restricted_statuses = ('left', 'kicked', 'restricted')


def new_player(call: telebot.types.CallbackQuery) -> (str, str):
    draw_id = int(call.data.split('_')[1])
    draw: models.Draw = middleware_base.get_one(models.Draw, id=draw_id, status='posted')

    if not draw:
        return 'no_draw_found', 'Розыгрыш не найден'

    text = get_vocabulary(draw.user_id)['draw']

    # @todo: check restricted hours

    player_id = call.from_user.id
    player = middleware_base.get_one(models.DrawPlayer, draw_id=str(draw_id), user_id=str(player_id))

    if player:
        return 'already_in', text['already_in']

    channels_to_subscribe = middleware_base.select_all(models.SubscribeChannel, draw_id=draw_id)

    for channel in channels_to_subscribe:
        chat_member = bot.get_chat_member(chat_id=channel.channel_id, user_id=player_id)
        if chat_member.status in get_on_restricted_statuses:
            return 'not_subscribed', text['not_subscribe']

    middleware_base.new(models.DrawPlayer, draw_id, str(player_id), str(call.from_user.username))

    total = middleware_base.count(models.DrawPlayer, draw_id=draw_id)

    return 'got_on', f"({total}) {text['play']}"


def render_my_channels_inline_keyboard(user_id: int) -> telebot.types.InlineKeyboardMarkup:
    voc = get_vocabulary(user_id)
    channels = middleware_base.select_all(models.MyChannel, user_id=str(user_id))

    values = dict()

    for x in channels:
        values[x.chanel_name or x.chanel_id] = {'callback_data': 'my_channels.view.{0}'.format(x.id)}
        values['Удалить #{0}'.format(x.id)] = {'callback_data': 'my_channels.delete.{0}'.format(x.id)}

    values[voc['my_channels']['add_new']] = {'callback_data': 'my_channels.add_new'}
    values['Закрыть'] = {'callback_data': 'close'}

    return telebot.util.quick_markup(values, row_width=2)


def render_choose_my_channel_inline_keyboard(user_id: int) -> telebot.types.InlineKeyboardMarkup:
    channels = middleware_base.select_all(models.MyChannel, user_id=str(user_id))

    values = dict()

    for x in channels:
        values[x.chanel_name or x.chanel_id] = {'callback_data': 'new_raffle.choose_my_channel.{0}'.format(x.id)}

    values['Закрыть'] = {'callback_data': 'close'}

    return telebot.util.quick_markup(values, row_width=1)


def render_is_random_inline_keyboard(user_id: int) -> telebot.types.InlineKeyboardMarkup:
    values = dict()
    values['Вручную'] = {'callback_data': 'new_raffle.is_random.no'}
    values['Автоматически'] = {'callback_data': 'new_raffle.is_random.yes'}
    values['В главное меню ↩️'] = {'callback_data': 'close'}
    return telebot.util.quick_markup(values, row_width=2)


def send_draw_message(chat_id: str, draw: models.Draw, draw_text: str, markup: telebot.types.ReplyKeyboardMarkup) -> telebot.types.Message:
    if draw.file_type == 'photo':
        return bot.send_photo(chat_id, draw.file_id, draw_text, reply_markup=markup)

    if draw.file_type == 'document':
        return bot.send_document(chat_id, draw.file_id, caption=draw_text, reply_markup=markup)

    return bot.send_message(chat_id, draw_text, reply_markup=markup)
