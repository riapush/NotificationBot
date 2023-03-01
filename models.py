from aiogram.dispatcher.filters.state import StatesGroup, State
from peewee import *

db = SqliteDatabase('notifications.db')


class Notification(Model):
    notification_id = AutoField()
    user_id = IntegerField(null=False)
    task = TextField(null=False)
    deadline = DateField(null=False)
    attachments = CharField(null=True)
    is_periodic = BooleanField(default=False)
    is_finished = BooleanField(default=False)

    class Meta:
        database = db

class NotificationForm(StatesGroup):
    task = State()
    deadline = State()
    attachments = State()
    is_periodic = State()
    is_finished = State()

class EditForm(StatesGroup):
    id = State()