from aiogram.dispatcher.filters.state import StatesGroup, State
from peewee import *

db = SqliteDatabase('notifications.db')


class Notification(Model):
    notification_id = AutoField()
    user_id = IntegerField(null=False)
    task = TextField(null=False)
    description = TextField(null=True)
    date = DateField(null=False)
    time = TimeField(null=False)
    attachments = BooleanField(default=False)
    is_periodic = BooleanField(default=False)
    is_edited = BooleanField(default=False)
    interval = IntegerField(null=True)
    is_finished = BooleanField(default=False)
    is_send = BooleanField(default=False)

    class Meta:
        database = db


class NotificationForm(StatesGroup):
    task = State()
    description = State()
    date = State()
    time = State()
    attachments = State()
    is_periodic = State()
    interval = State()
    is_finished = State()
    notification_id = State()


class ChooseForm(StatesGroup):
    id = State()
    date = State()
    time = State()
    description = State()
    current = State()
    attachments = State()
