from aiogram.dispatcher.filters.state import StatesGroup, State
from peewee import *

db = SqliteDatabase('notifications.db')


class Notification(Model):
    notification_id = AutoField()
    user_id = IntegerField(null=False)
    task = TextField(null=False)
    date = DateField(null=False)
    time = TimeField(default='10:00')
    attachments = CharField(null=True)
    is_periodic = BooleanField(default=False)
    is_finished = BooleanField(default=False)
    is_send = BooleanField(default=False)

    class Meta:
        database = db

class NotificationForm(StatesGroup):
    task = State()
    date = State()
    time = State()
    attachments = State()
    is_periodic = State()
    is_finished = State()

class ChooseForm(StatesGroup):
    id = State()
