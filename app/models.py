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
    user_id = Column(String, primary_key=True)
    user_name = Column(String)
    language = Column(String)

    def __init__(self, user_id, user_name, language):
        self.user_id = user_id
        self.user_name = user_name
        self.language = language

    def __repr__(self):
        return "<User(user_id='%s', user_name='%s', language='%s')>" % (
            self.user_id, self.user_name, self.language)


class DrawProgress(Base):
    __tablename__ = 'draw_progress'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    chanel_id = Column(String, index=True)
    chanel_name = Column(String)
    text = Column(String)
    file_type = Column(String)
    file_id = Column(String)
    post_time = Column(String)
    end_time = Column(String)

    def __init__(self, user_id, chanel_id, chanel_name, text, file_type, file_id, post_time, end_time):
        self.user_id = str(user_id)
        self.chanel_id = str(chanel_id)
        self.chanel_name = chanel_name
        self.text = text
        self.file_type = file_type
        self.file_id = file_id
        self.post_time = post_time
        self.end_time = end_time

    def __repr__(self):
        return "<DrawProgress(id=%d, user_id='%s', chanel_id='%s', chanel_name='%s', text='%s', file_type='%s', file_id='%s', post_time='%s', end_time='%s')>" % (
            self.id,
            self.user_id,
            self.chanel_id,
            self.chanel_name,
            self.text,
            self.file_type,
            self.file_id,
            self.post_time,
            self.end_time)


class DrawNot(Base):
    __tablename__ = 'not_posted'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    chanel_id = Column(String, index=True)
    chanel_name = Column(String)
    text = Column(String)
    file_type = Column(String)
    file_id = Column(String)
    post_time = Column(String)
    end_time = Column(String)

    def __init__(self, draw_id, user_id, chanel_id, chanel_name, text, file_type, file_id, post_time, end_time):
        self.id = draw_id
        self.user_id = str(user_id)
        self.chanel_id = str(chanel_id)
        self.chanel_name = chanel_name
        self.text = text
        self.file_type = file_type
        self.file_id = file_id
        self.post_time = post_time
        self.end_time = end_time

    def __repr__(self):
        return "<DrawNot(id=%d, user_id='%s', chanel_id='%s', chanel_name='%s', text='%s', file_type='%s', file_id='%s', post_time='%s', end_time='%s')>" % (
            self.id,
            self.user_id,
            self.chanel_id,
            self.chanel_name,
            self.text,
            self.file_type,
            self.file_id,
            self.post_time,
            self.end_time)


class Draw(Base):
    __tablename__ = 'draw'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    message_id = Column(String)
    chanel_id = Column(String, index=True)
    chanel_name = Column(String)
    text = Column(String)
    file_type = Column(String)
    file_id = Column(String)
    post_time = Column(String)
    end_time = Column(String)

    def __init__(self, draw_id, user_id, message_id, chanel_id, chanel_name, text, file_type, file_id, post_time, end_time):
        self.id = draw_id
        self.user_id = str(user_id)
        self.message_id = str(message_id)
        self.chanel_id = str(chanel_id)
        self.chanel_name = chanel_name
        self.text = text
        self.file_type = file_type
        self.file_id = file_id
        self.post_time = post_time
        self.end_time = end_time

    def __repr__(self):
        return "<Draw(id=%d, user_id='%s', message_id='%s' chanel_id='%s', chanel_name='%s', text='%s', file_type='%s', file_id='%s', post_time='%s', end_time='%s')>" % (
            self.id,
            self.user_id,
            self.message_id,
            self.chanel_id,
            self.chanel_name,
            self.text,
            self.file_type,
            self.file_id,
            self.post_time,
            self.end_time)


class SubscribeChannel(Base):
    __tablename__ = 'channel'
    id = Column(Integer, primary_key=True)
    draw_id = Column(Integer, index=True)
    user_id = Column(String, index=True)
    channel_id = Column(String, index=True)

    def __init__(self, draw_id, user_id, channel_id):
        self.draw_id = draw_id
        self.user_id = user_id
        self.channel_id = channel_id

    def __repr__(self):
        return "<channel(id=%d, draw_id=%d, user_id='%s', channel_id='%s')>" % (
            self.id, self.draw_id, self.user_id, self.channel_id)


class DrawPlayer(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    draw_id = Column(Integer, index=True)
    user_id = Column(String, index=True)
    user_name = Column(String)

    def __init__(self, draw_id, user_id, user_name):
        self.draw_id = draw_id
        self.user_id = user_id
        self.user_name = user_name

    def __repr__(self):
        return "<Player(draw_id='%s', user_id='%s', user_name='%s')>" % (
            self.draw_id, self.user_id, self.user_name)


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
        return "<State(user_id='%s', state='%s', arg='%s')>" % (
            self.user_id, self.state, self.arg)


class MyChannel(Base):
    __tablename__ = 'my_channels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    chanel_id = Column(String, index=True)
    chanel_name = Column(String)

    def __init__(self, user_id: int, chanel_id: str, chanel_name=''):
        self.user_id = user_id
        self.chanel_id = chanel_id
        self.chanel_name = chanel_name

    def __repr__(self):
        return "<MyChannel(id=%s, user_id=%d, chanel_id='%s', chanel_name='%s')>" % (
            self.id, self.user_id, self.chanel_id, self.chanel_name)


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
