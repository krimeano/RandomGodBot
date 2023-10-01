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
                        print('EXCEPT', 'start_draw_timer timer', exception)
                        post_base.update(models.Draw, {'status': 'archived'}, id=item.id)
            time.sleep(10)

    r_t = threading.Thread(target=timer)
    r_t.start()


def end_draw_timer():
    def end_timer():
        while 1:
            for item in end_base.select_all(models.Draw, status='posted'):
                if not bot_lib.is_time_less_or_equal(item.end_time):
                    continue

                text = language_check(item.user_id)[1]['draw']
                try:
                    define_winners(item)
                    owin, winners = render_winners(item)
                    bot.send_message(chat_id=str(item.chanel_id), text=winners, parse_mode='HTML')

                except Exception as exception:
                    print('EXCEPT', 'end_timer', exception)
                    end_base.update(models.Draw, {'status': 'archived'}, id=item.id)
                    bot.send_message(item.chanel_id, text['failed_post'])
                    break

                bot.send_message(item.user_id, f"{text['your_draw_over']}\n{owin}", parse_mode='HTML')
                end_base.update(models.Draw, {'status': 'archived'}, id=item.id)
                break

            time.sleep(10)

    r_t = threading.Thread(target=end_timer)
    r_t.start()


def define_winners(draw: models.Draw):
    if draw.status != 'posted':
        raise Exception('draw is not posted')

    players: list[models.DrawPlayer] = end_base.select_all(models.DrawPlayer, draw_id=draw.id)
    players_map = dict((normalize_username(x.user_name), x) for x in players)

    prizes: list[models.DrawPrize] = end_base.select_all(models.DrawPrize, draw_id=draw.id)

    manual_player_usernames: list[str] = []

    players_to_raffle = 0

    for prize in prizes:
        if prize.preset_winners:
            usernames = [normalize_username(x) for x in prize.preset_winners.split(', ')]
            manual_player_usernames += usernames
        else:
            players_to_raffle += prize.winners_count

    player_usernames: list[str] = [x for x in players_map if x not in manual_player_usernames]

    winner_usernames: list[str] = []

    while len(winner_usernames) < players_to_raffle and len(player_usernames) > 0:
        username = random.choice(player_usernames)
        player_usernames.remove(username)
        winner_usernames.append(username)

    for prize in prizes:
        if prize.preset_winners:
            usernames = [normalize_username(x) for x in prize.preset_winners.split(', ')]
            for username in usernames:
                user_id = username in players_map and players_map[username].user_id or ''
                end_base.new(models.DrawWinner, draw.id, prize.id, user_id, username)
        else:
            for ix in range(prize.winners_count):
                if not len(winner_usernames):
                    break
                username = winner_usernames.pop(0)
                player = players_map[username]
                end_base.new(models.DrawWinner, draw.id, prize.id, player.user_id, username)


def normalize_username(username: str) -> str:
    if username[0] != '@':
        return '@' + username

    return username


def render_winners(draw: models.Draw) -> (str, str):
    text = language_check(draw.user_id)[1]['draw']
    draw_winners: list[models.DrawWinner] = end_base.select_all(models.DrawWinner, draw_id=draw.id)

    if not draw_winners:
        return f"{text['no_winners']}", f"{draw.text}\n*****\n{text['no_winners']}"

    prizes: list[models.DrawPrize] = end_base.select_all(models.DrawPrize, draw_id=draw.id)
    winners = f"{draw.text}\n*****\n{text['winners']}\n"
    owin = f"{text['winners']}\n"

    for prize in prizes:
        prize_winners = [x for x in draw_winners if x.prize_id == prize.id]
        if not prize_winners:
            continue
        prize_text = '\n'.join([winner_to_link(x) for x in prize_winners]) + '\n' + prize.description + '\n'
        winners += prize_text
        owin += prize_text

    return owin, winners


def winner_to_link(draw_winner: models.DrawWinner) -> str:
    if draw_winner.user_id:
        return f"<a href='tg://user?id={draw_winner.user_id}'>{draw_winner.user_name}</a>"
    return draw_winner.user_name


# get_on_restricted_statuses = ('left', 'kicked', 'restricted', 'administrator', 'creator')
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
