from sqlalchemy import Column, Integer, String, LargeBinary
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

import config

# ---INIT---
engine = create_engine(config.db_url, echo=False)
session = scoped_session(sessionmaker(bind=engine, autoflush=False))
Base = declarative_base()


class User(Base):
    __tablename__ = 'bot_user'
    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    language = Column(String)

    def __init__(self, user_id: int, username: str, language='RU'):
        self.user_id = user_id
        self.username = username
        self.language = language

    def __repr__(self):
        return "<User(user_id=%d, username='%s', language='%s')>" % (
            self.user_id, self.username, self.language)


# statuses: progress -> not_posted -> posted -> archived
class Draw(Base):
    __tablename__ = 'draw'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    channel_id = Column(String, index=True)
    channel_name = Column(String)
    text = Column(String)
    file_type = Column(String)
    file_id = Column(String)
    post_time = Column(String)
    end_time = Column(String)
    restricted_hours = Column(Integer, default=0)
    status = Column(String, default='progress', index=True)
    message_id = Column(Integer, nullable=True, index=True)

    def __init__(self, user_id: int, channel_id: str, channel_name: str, text: str, file_type: str, file_id: str, post_time: str, end_time: str, restricted_hours: int):
        self.user_id = user_id
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.text = text
        self.file_type = file_type
        self.file_id = file_id
        self.post_time = post_time
        self.end_time = end_time
        self.restricted_hours = restricted_hours

    def __repr__(self):
        return "<Draw(id=%d, user_id=%d, channel_id='%s', channel_name='%s', text='%s', file_type='%s', file_id='%s', post_time='%s', end_time='%s', restricted_hours=%d, status='%s', message_id=%d)>" % (
            self.id,
            self.user_id,
            self.channel_id,
            self.channel_name,
            self.text,
            self.file_type,
            self.file_id,
            self.post_time,
            self.end_time,
            self.restricted_hours,
            self.status,
            self.message_id,
        )


class SubscribeChannel(Base):
    __tablename__ = 'channel'
    id = Column(Integer, primary_key=True)
    draw_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    channel_id = Column(String, index=True)

    def __init__(self, draw_id: int, user_id: int, channel_id: str):
        self.draw_id = draw_id
        self.user_id = user_id
        self.channel_id = channel_id

    def __repr__(self):
        return "<channel(id=%d, draw_id=%d, user_id=%d, channel_id='%s')>" % (
            self.id, self.draw_id, self.user_id, self.channel_id)


class DrawPlayer(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    draw_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    username = Column(String, default='')
    first_name = Column(String, default='')
    last_name = Column(String, default='')

    def __init__(self, draw_id: int, user_id: int, username='', first_name='', last_name=''):
        self.draw_id = draw_id
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name

    def __repr__(self):
        return "<Player(draw_id=%d, user_id=%d, username='%s', first_name='%s', last_name='%s')>" % (
            self.draw_id, self.user_id, self.username, self.first_name, self.last_name)


class State(Base):
    __tablename__ = 'user_state'
    user_id = Column(Integer, primary_key=True)
    state = Column(String)
    arg = Column(LargeBinary)

    def __init__(self, user_id, state, arg):
        self.user_id = user_id
        self.state = state
        self.arg = arg

    def __repr__(self):
        return "<State(user_id=%d, state='%s', arg='%s')>" % (
            self.user_id, self.state, self.arg)


class MyChannel(Base):
    __tablename__ = 'my_channels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    channel_id = Column(String, index=True)
    channel_name = Column(String)

    def __init__(self, user_id: int, channel_id: str, channel_name=''):
        self.user_id = user_id
        self.channel_id = channel_id
        self.channel_name = channel_name

    def __repr__(self):
        return "<MyChannel(id=%s, user_id=%d, channel_id='%s', channel_name='%s')>" % (
            self.id, self.user_id, self.channel_id, self.channel_name)


class DrawPrize(Base):
    __tablename__ = 'draw_prize'
    id = Column(Integer, primary_key=True, autoincrement=True)
    draw_id = Column(Integer, index=True)
    winners_count = Column(Integer)
    description = Column(String)
    preset_winners = Column(String)

    def __init__(self, draw_id: int, winners_count: int, description: str, preset_winners: list[str]):
        self.draw_id = draw_id
        self.winners_count = winners_count
        self.description = description
        self.preset_winners = ', '.join(preset_winners)

    def __repr__(self):
        return "<DrawPrize(id=%s, draw_id=%d, winners_count=%d, description='%s', preset_winners=%s)>" % (
            self.id, self.draw_id, self.winners_count, self.description, self.preset_winners)


class DrawWinner(Base):
    __tablename__ = 'draw_winner'
    id = Column(Integer, primary_key=True, autoincrement=True)
    draw_id = Column(Integer, index=True)
    prize_id = Column(Integer)
    user_id = Column(Integer)
    username = Column(String)
    display_name = Column(String)

    def __init__(self, draw_id: int, prize_id: int, user_id: int, username='', display_name=''):
        self.draw_id = draw_id
        self.prize_id = prize_id
        self.user_id = user_id
        self.username = username
        self.display_name = display_name

    def __repr__(self):
        return "<DrawWinner(id=%s, draw_id=%d, prize_id=%d, user_id=%d, username='%s', display_name='%s')>" % (
            self.id, self.draw_id, self.prize_id, self.user_id, self.username, self.display_name)
