import random
import threading
import time

import telebot.types

import bot_lib
import keyboard
import models
from app import middleware_base, bot, post_base, end_base
from tool import language_check, create_inline_keyboard, get_vocabulary


def check_user(user_id):
    user = middleware_base.get_one(models.User, user_id=str(user_id))
    if user is not None:
        return user
    else:
        return False


def create_draw_progress(user_id, tmp):
    middleware_base.delete(models.Draw, user_id=str(user_id), status='progress')

    prizes = tmp['prizes']  # [[0, '', False, []]]

    draw = middleware_base.new(
        models.Draw,
        str(user_id), tmp['chanel_id'], tmp['chanel_name'], tmp['draw_text'], tmp['file_type'], tmp['file_id'], tmp['start_time'], tmp['end_time']
    )

    for prize in prizes:
        [winners_count, description, is_manual, preset_winners] = prize
        middleware_base.new(
            models.DrawPrize,
            draw.id, int(winners_count), description, preset_winners
        )

    middleware_base.delete(models.State, user_id=str(user_id))

    return draw_info(user_id)


def draw_info(user_id):
    tmp = check_post(str(user_id))
    text = language_check(user_id)[1]['draw']
    return f"{text['change_text']}\n{text['post_time_text']} {tmp.post_time}\n{text['over_time_text']} {tmp.end_time}\n{text['chanel/chat']} {tmp.chanel_name}\n{text['count_text']}\n{text['text']} {tmp.text}"


def check_post(user_id):
    return middleware_base.get_one(models.Draw, user_id=str(user_id), status='progress')


def send_draw_info(user_id):
    tmp = check_post(str(user_id))
    text = language_check(user_id)[1]['draw']
    draw_text = f"{text['change_text']}\n{text['post_time_text']} {tmp.post_time}\n{text['over_time_text']} {tmp.end_time}\n{text['chanel/chat']} {tmp.chanel_name}\n{text['count_text']}\n{text['text']} {tmp.text}"

    if tmp.file_type == 'photo':
        bot.send_photo(user_id, tmp.file_id, draw_text, reply_markup=keyboard.get_draw_keyboard(user_id))

    if tmp.file_type == 'document':
        bot.send_document(user_id, tmp.file_id, caption=draw_text, reply_markup=keyboard.get_draw_keyboard(user_id))

    else:
        bot.send_message(user_id, draw_text, reply_markup=keyboard.get_draw_keyboard(user_id))

    middleware_base.delete(models.State, user_id=user_id)


def my_draw_info(user_id, row=0):
    if row < 0:
        return 'first'

    text = language_check(user_id)[1]['my_draw']
    not_posted = middleware_base.select_all(models.Draw, user_id=str(user_id), status='not_posted')
    posted = middleware_base.select_all(models.Draw, user_id=str(user_id), status='posted')
    all_draws = not_posted + posted
    if len(all_draws) == 0:
        bot.send_message(user_id, text['no_draw'])
        return

    if row >= len(all_draws):
        print('notttt')
        return 'last'  # @todo not sure

    draw_text = f"{text['your_draw']}\n{text['post_time_text']} {all_draws[row].post_time}\n{text['over_time_text']} {all_draws[row].end_time}\n{text['chanel/chat']} {all_draws[row].chanel_name}\n{text['count_text']}\n{text['text']} {all_draws[row].text}"
    keyboard_markup = create_inline_keyboard({text['back']: "back", text['next']: "next"}, 2)
    if all_draws[row].file_type == 'photo':
        bot.send_photo(user_id, all_draws[row].file_id, draw_text, reply_markup=keyboard_markup)
    elif all_draws[row].file_type == 'document':
        bot.send_document(user_id, all_draws[row].file_id, caption=draw_text, reply_markup=keyboard_markup)
    else:
        bot.send_message(user_id, draw_text, reply_markup=keyboard_markup)


def start_draw_timer():
    def timer():
        while 1:
            for item in post_base.select_all(models.Draw, status='not_posted'):

                if bot_lib.is_time_less_or_equal(item.post_time):

                    if item.file_type == 'photo':
                        tmz = bot.send_photo(item.chanel_id, item.file_id, item.text,
                                             reply_markup=create_inline_keyboard({language_check(item.user_id)[1]['draw']['get_on']: f'geton_{item.id}'}))

                    elif item.file_type == 'document':
                        tmz = bot.send_document(item.chanel_id, item.file_id, caption=item.text,
                                                reply_markup=create_inline_keyboard({language_check(item.user_id)[1]['draw']['get_on']: f'geton_{item.id}'}))
                    else:
                        tmz = bot.send_message(item.chanel_id, item.text,
                                               reply_markup=create_inline_keyboard({language_check(item.user_id)[1]['draw']['get_on']: f'geton_{item.id}'}))

                    post_base.update(models.Draw, {'message_id': tmz.message_id, 'status': 'posted'}, id=item.id)

            time.sleep(5)

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


def new_player(call):
    player_id = int(call.data.split('_')[1])
    tmp = middleware_base.get_one(models.Draw, id=player_id, status='posted')
    chanel = middleware_base.select_all(models.SubscribeChannel, draw_id=tmp.id)
    status = ['left', 'kicked', 'restricted', 'member', 'administrator', 'creator']
    for i in chanel:
        if bot.get_chat_member(chat_id=i.channel_id, user_id=call.from_user.id).status in status:
            return 'not_subscribed'  # @todo different return signature

    players = middleware_base.get_one(models.DrawPlayer, draw_id=str(tmp.id), user_id=str(call.from_user.id))

    if players is None:
        middleware_base.new(models.DrawPlayer, tmp.id, str(call.from_user.id), str(call.from_user.username))
        tmz = middleware_base.select_all(models.DrawPlayer, draw_id=tmp.id)
        return len(tmz), language_check(tmp.user_id)[1]['draw']['play']
    else:
        return False


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
