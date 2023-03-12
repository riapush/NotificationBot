from datetime import date, datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
import logging
import asyncio
import aioschedule
from models import Notification, NotificationForm, ChooseForm, ReturnForm
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram_timepicker.panel import FullTimePicker, full_timep_callback

API_TOKEN = '5714223753:AAHVAo2WiT3-1M7JzYfCr_d5uHfk6EpsZSA'
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
Notification.create_table()


async def scheduler():
    aioschedule.every(60).seconds.do(check_notification_time)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


async def check_notification_time():
    to_notify = Notification.select().where((Notification.date == date.today()) & (Notification.time < datetime.now().strftime("%H:%M:%S")) &
                                (Notification.is_finished == False) & (Notification.is_send == False))
    for task in to_notify:
        print(task)
        msg = f'Привет! Ты просила - я напоминаю\n\n' \
              f'id: {task.notification_id}\n' \
              f'Задание: {task.task}\n' \
              f'{"Описание: " + str(task.description) if task.description else ""}\n' \
              f'Дата напоминания: {task.date}\n' \
              f'Регулярное ли задание: {"Да" if task.is_periodic == True else "Нет"}\n\n'
        if task.is_periodic:
            Notification.create(user_id=task.user_id, task=task.task, description=task.description,
                                date=task.date + timedelta(days=task.interval), time=task.time,
                                is_periodic=task.is_periodic, is_finished=False)
        task.is_send = True
        task.save()
        await bot.send_message(task.user_id, msg)


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


@dp.callback_query_handler(text="finished_tasks")
async def finished_tasks(callback: types.CallbackQuery):
    tasks = Notification.select().where((Notification.user_id == callback.message.chat.id) & (Notification.is_finished == True))
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    if len(tasks) == 0:
        msg = "Тут пусто."
    else:
        msg = "Вот, что ты уже сделала: \n\n"
        for task in tasks:
            msg += f'id: {task.notification_id}\n' \
                   f'Задание: {task.task}\n' \
                   f'{"Описание: " + str(task.description) if task.description else ""}\n' \
                   f'Дата напоминания: {task.date}\n' \
                   f'Регулярное ли задание: {"Да" if task.is_periodic == True else "Нет"}\n\n'
        kb.add(types.InlineKeyboardButton(text="Вернуть дело в текущие", callback_data="return_notification"))
    await callback.message.answer(msg, reply_markup=kb)


@dp.callback_query_handler(text="return_notification")
async def return_notification(callback: types.CallbackQuery):
    await ChooseForm.id.set()
    await callback.message.answer("Введи id задачи, которую хочешь вернуть в текущие.")


@dp.callback_query_handler(text="add_notification")
async def add_notification(callback: types.CallbackQuery):
    await NotificationForm.task.set()
    await callback.message.answer("Вещай, красотка! Может быть, я и не могу выполнять дела за тебя "
                        "(у любой магии есть свои лимиты), но за помощью ты правильно пришла!\n"
                                  "Введи название задачи:")


@dp.message_handler(state=NotificationForm.task)
async def add_description(message: types.Message, state: FSMContext):
    await state.update_data(task=message.text)
    await NotificationForm.description.set()
    await message.reply("Введи описание задачи. Чтобы оставить это поле пустым, введи /skip")


@dp.message_handler(state=NotificationForm.description)
async def add_date(message: types.Message, state: FSMContext):
    if message.text != '/skip':
        await state.update_data(description=message.text)
    await NotificationForm.date.set()
    await message.reply("Когда отправить напоминание?", reply_markup=await SimpleCalendar().start_calendar())


@dp.callback_query_handler(simple_cal_callback.filter(), state=NotificationForm.date)
async def add_time(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(f'Ты выбрала {date.strftime("%d/%m/%Y")}', reply_markup=None)
        await state.update_data(date=date)
        await state.set_state(NotificationForm.time)
        await callback_query.message.answer("Во сколько напомнить? ", reply_markup=await FullTimePicker().start_picker())


@dp.callback_query_handler(full_timep_callback.filter(), state=NotificationForm.time)
async def is_periodic(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    r = await FullTimePicker().process_selection(callback_query, callback_data)
    if r.selected:
        await callback_query.message.answer(
            f'Ты выбрала {r.time.strftime("%H:%M:%S")}', reply_markup=None)
        await state.update_data(time=r.time)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        kb.add("Да", "Нет")
        await state.set_state(NotificationForm.is_periodic)
        await callback_query.message.answer("Регулярное ли задание?", reply_markup=kb)


@dp.message_handler(state=NotificationForm.is_periodic)
async def add_attachments(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        await state.update_data(is_periodic=True)
        await state.set_state(NotificationForm.interval)
        await message.reply("Как часто повторять напоминание? Введи количество дней.")
    else:
        await state.update_data(is_periodic=False)
        await state.set_state(NotificationForm.attachments)
        kb = types.InlineKeyboardMarkup(resize_keyboard=True)
        kb.add(types.InlineKeyboardButton(text="Да", callback_data="attach"))
        kb.add(types.InlineKeyboardButton(text="Нет", callback_data="no_attach"))
        await message.reply("Добавить вложения?", reply_markup=kb)


@dp.message_handler(state=NotificationForm.interval)
async def add_interval(message: types.Message, state: FSMContext):
    await state.update_data(interval=int(message.text))
    await state.set_state(NotificationForm.attachments)
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    kb.add(types.InlineKeyboardButton(text="Да", callback_data="attach"))
    kb.add(types.InlineKeyboardButton(text="Нет", callback_data="no_attach"))
    await message.reply("Добавить вложения?", reply_markup=kb)


@dp.callback_query_handler(state=NotificationForm.attachments, text="no_attach")
async def process_attachments(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    print(data)
    try:
        Notification.create(user_id=callback.message.chat.id, task=data['task'], description=data['description'],
                            date=data['date'], time=data['time'], is_periodic=data['is_periodic'],
                            interval=data['interval'], is_finished=False)
    except KeyError:
        Notification.create(user_id=callback.message.chat.id, task=data['task'], date=data['date'], time=data['time'],
                            is_periodic=data['is_periodic'], interval=data['interval'], is_finished=False)
    await state.finish()
    await callback.message.answer("Напоминание успешно установлено")


@dp.callback_query_handler(state=NotificationForm.attachments, text="attach")
async def process_attachments(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправь вложение следующим сообщением")


@dp.callback_query_handler(text="check_tasks")
async def check_tasks(callback: types.CallbackQuery):
    tasks = Notification.select().where((Notification.user_id == callback.message.chat.id) & (Notification.is_finished == False))
    if len(tasks) == 0:
        msg = "У тебя еще не запланировано никаких дел."
        kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    else:
        msg = "Вот, что тебе нужно сделать: \n\n"
        kb = types.InlineKeyboardMarkup(resize_keyboard=True)
        kb.add(types.InlineKeyboardButton(text="Выбрать напоминание", callback_data="choose_notification"))
        for task in tasks:
            msg += f'id: {task.notification_id}\n' \
                   f'Задание: {task.task}\n' \
                   f'{"Описание: " + str(task.description) if task.description else ""}\n' \
                   f'Дата напоминания: {task.date}\n' \
                   f'Время: {task.time}\n' \
                   f'Регулярное ли задание: {"Да" if task.is_periodic == True else "Нет"}\n\n'
    await callback.message.answer(msg, reply_markup=kb)


@dp.callback_query_handler(text="choose_notification")
async def choose_notification(callback: types.CallbackQuery):
    await ChooseForm.id.set()
    await callback.message.answer("Введи id напоминания для изменения: ")


@dp.message_handler(lambda message: message.text.isdigit(), state=ChooseForm.id)
async def process_notification_id(message: types.Message, state: FSMContext):
    try:
        instance = Notification.get_by_id(int(message.text))
        if instance.user_id != message.chat.id:
            await message.reply("Ошибка, такого напоминания нет, попробуйте заново")
        else:
            if instance.is_finished:
                instance.is_finished = False
                instance.save()
                await state.update_data(id=int(message.text))
                await ChooseForm.date.set()
                await message.answer(f"Введите новую дату: ", reply_markup=await SimpleCalendar().start_calendar())
            else:
                await state.update_data(id=int(message.text))
                kb = types.InlineKeyboardMarkup(resize_keyboard=True)
                kb.add(types.InlineKeyboardButton(text="Удалить напоминание", callback_data="delete_notification"))
                kb.add(types.InlineKeyboardButton(text="Редактировать напоминание", callback_data="edit_notification"))
                kb.add(types.InlineKeyboardButton(text="Отметить выполненным", callback_data="finish_notification"))
                await message.answer(f"Выбранное напоминание: {message.text}", reply_markup=kb)
    except:
        await message.reply("Ошибка, такого напоминания нет, попробуйте заново")


@dp.callback_query_handler(text="delete_notification", state=ChooseForm)
async def delete_notification(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    Notification.delete_by_id(data['id'])
    await state.finish()
    await callback.message.answer(f"Напоминание с id={data['id']} удалено.")


@dp.callback_query_handler(text="finish_notification", state=ChooseForm)
async def finish_notification(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    instance = Notification.get_by_id(data['id'])
    instance.is_finished = True
    instance.save()
    await state.finish()
    await callback.message.answer(f"Напоминание с id={data['id']} отмечено выполненным.")


@dp.callback_query_handler(text="edit_notification", state=ChooseForm)
async def edit_notification(callback: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(resize_keyboard=True)
    kb.add(types.InlineKeyboardButton(text="Редактировать дату", callback_data="edit_date"))
    kb.add(types.InlineKeyboardButton(text="Редактировать время", callback_data="edit_time"))
    kb.add(types.InlineKeyboardButton(text="Редактировать описание", callback_data="edit_task"))
    await callback.message.answer(f"Что будем редактировать? ", reply_markup=kb)


@dp.callback_query_handler(text="edit_task", state=ChooseForm)
async def edit_task_input(callback: types.CallbackQuery, state: FSMContext):
    await ChooseForm.description.set()
    await callback.message.answer(f"Введите новое описание: ")


@dp.message_handler(state=ChooseForm.description)
async def edit_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    instance = Notification.get_by_id(data['id'])
    instance.description = data['description']
    instance.save()
    await state.finish()
    await message.answer(f'Описание изменено.', reply_markup=None)



@dp.callback_query_handler(text="edit_date", state=ChooseForm)
async def edit_date_input(callback: types.CallbackQuery, state: FSMContext):
    await ChooseForm.date.set()
    await callback.message.answer(f"Введите новую дату: ", reply_markup=await SimpleCalendar().start_calendar())


@dp.callback_query_handler(simple_cal_callback.filter(), state=ChooseForm.date)
async def edit_date(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(f'Ты выбрала {date.strftime("%d/%m/%Y")}. Дата изменена.', reply_markup=None)
        await state.update_data(date=date)
        data = await state.get_data()
        print(data)
        instance = Notification.get_by_id(data['id'])
        instance.date = data['date']
        instance.save()
        await state.finish()


@dp.callback_query_handler(text="edit_time", state=ChooseForm)
async def edit_time_input(callback: types.CallbackQuery, state: FSMContext):
    await ChooseForm.time.set()
    await callback.message.answer(f"Введите новое время: ", reply_markup=await FullTimePicker().start_picker())


@dp.callback_query_handler(full_timep_callback.filter(), state=ChooseForm.time)
async def edit_time(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    r = await FullTimePicker().process_selection(callback_query, callback_data)
    if r.selected:
        await callback_query.message.answer(
            f'Ты выбрала {r.time.strftime("%H:%M:%S")}. Время изменено.', reply_markup=None)
        await state.update_data(time=r.time)
        data = await state.get_data()
        print(data)
        instance = Notification.get_by_id(data['id'])
        instance.time = data['time']
        instance.save()
        await state.finish()


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer("Смотри, что я могу:\n"
                         "Я умею создавать задачу по кнопке 'Напоминание добавлямус!' и уведомлять о делах в нужное время\n"
                         "")


@dp.message_handler()
async def unknown_message(message: types.Message):
    await message.answer("Я тебя не понимаю :(\n")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)