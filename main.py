from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup
import logging
from models import Notification, NotificationForm, EditForm

API_TOKEN = '5714223753:AAHVAo2WiT3-1M7JzYfCr_d5uHfk6EpsZSA'
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
Notification.create_table()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    kb.add(types.InlineKeyboardButton(text="Напоминание добавлямус!", callback_data="add_notification"))
    kb.add(types.InlineKeyboardButton(text="Важности!!", callback_data="check_tasks"))
    kb.add(types.InlineKeyboardButton(text="Кнопка, чтобы вспомнить, кто хорошая девочка!",
                                      callback_data="finished_tasks"))
    await message.answer("Привет, подружка!\n"
                        "Я твоя фея-помощница! Со мной и каплей моей магии твои дела "
                         "будут выполняться по взмаху волшебной палочки.\n"
                         "А чтобы узнать, что я могу, используй заклинание /help", reply_markup=kb)


@dp.callback_query_handler(text="add_notification")
async def add_notification(callback: types.CallbackQuery):
    await NotificationForm.task.set()
    await callback.message.answer("Вещай, красотка! Может быть, я и не могу выполнять дела за тебя "
                        "(у любой магии есть свои лимиты), но за помощью ты правильно пришла!")


@dp.message_handler(state=NotificationForm.task)
async def add_deadline(message: types.Message, state: FSMContext):
    await state.update_data(task=message.text)
    await NotificationForm.deadline.set()
    await message.reply("Когда дедлайн?")


@dp.message_handler(state=NotificationForm.deadline)
async def is_periodic(message: types.Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    kb.add("Да", "Нет")
    await state.set_state(NotificationForm.is_periodic)
    await message.reply("Регулярное ли задание?", reply_markup=kb)


@dp.message_handler(state=NotificationForm.is_periodic)
async def add_attachments(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        await state.update_data(is_periodic=True)
    else:
        await state.update_data(is_periodic=False)
    """kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    kb.add(types.InlineKeyboardButton(text="Да", callback_data="yes_attach"))
    kb.add(types.InlineKeyboardButton(text="Нет", callback_data="no_attach"))
    await message.reply("Добавить вложения?", reply_markup=kb)"""
    data = await state.get_data()
    print(data, message.chat.id)
    print(Notification.create(user_id=message.chat.id, task=data['task'], deadline=data['deadline'], is_periodic=data['is_periodic']))
    await state.finish()


@dp.callback_query_handler(text="check_tasks")
async def check_tasks(callback: types.CallbackQuery):
    tasks = Notification.select().where(Notification.user_id==callback.message.chat.id)
    msg = "Вот, что тебе нужно сделать: \n\n"
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    kb.add(types.InlineKeyboardButton(text="Редактировать напоминание", callback_data="edit_notification"))
    for task in tasks:
        msg += f'id: {task.notification_id}\n' \
                   f'Задание: {task.task}\n' \
                   f'Дата напоминания: {task.deadline}\n\n'
    await callback.message.answer(msg, reply_markup=kb)

@dp.callback_query_handler(text="edit_notification")
async def edit_notification(callback: types.CallbackQuery):
    await EditForm.id.set()
    await callback.message.answer("Введи id напоминания для изменения: ")

@dp.message_handler(lambda message: message.text.isdigit(), state=EditForm.id)
async def process_notification_id(message: types.Message, state: FSMContext):
    await state.update_data(id=message.text)
    await message.answer("got id")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)