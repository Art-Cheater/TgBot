import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import database as db
from config import API_TOKEN, CHANNEL_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Создаем клавиатуру с кнопками
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    create_button = KeyboardButton('Создать объявление')
    my_ads_button = KeyboardButton('Мои объявления')
    keyboard.add(create_button, my_ads_button)
    return keyboard


def confirm_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    yes_button = KeyboardButton("Да")
    no_button = KeyboardButton("Нет")
    keyboard.add(yes_button, no_button)
    return keyboard


def edit_choice_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    title_button = KeyboardButton("Название")
    description_button = KeyboardButton("Описание")
    photo_button = KeyboardButton("Фото")
    price_button = KeyboardButton("Цена")
    keyboard.add(title_button, description_button, photo_button, price_button)
    return keyboard


def cancel_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('Отмена'))


class AdCreation(StatesGroup):
    title = State()
    description = State()
    photo = State()
    price = State()
    confirm = State()


class AdEditing(StatesGroup):
    ad_id = State()
    title = State()
    description = State()
    photo = State()
    price = State()
    confirm = State()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user = db.get_user(message.from_user.id)
    if user:
        await message.reply("Вы уже зарегистрированы.", reply_markup=main_menu_keyboard())
    else:
        db.add_user(message.from_user.id, message.from_user.username)
        await message.reply("Вы успешно зарегистрированы!", reply_markup=main_menu_keyboard())


@dp.message_handler(lambda message: message.text == "Создать объявление")
async def new_ad(message: types.Message):
    await AdCreation.title.set()
    await message.reply("Введите название объявления:", reply_markup=cancel_keyboard())


@dp.message_handler(state=AdCreation.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await AdCreation.next()
    await message.reply("Введите описание объявления:", reply_markup=cancel_keyboard())


@dp.message_handler(state=AdCreation.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await AdCreation.next()
    await message.reply("Пришлите фото объявления (или нажмите 'Отмена', если не хотите прикреплять фото):")


@dp.message_handler(content_types=['photo'], state=AdCreation.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await AdCreation.next()
    await message.reply("Введите цену объявления:", reply_markup=cancel_keyboard())


@dp.message_handler(lambda message: not message.text.isdigit(), state=AdCreation.price)
async def process_price_invalid(message: types.Message):
    return await message.reply("Пожалуйста, введите цену числом.", reply_markup=cancel_keyboard())


@dp.message_handler(state=AdCreation.price)
async def process_price(message: types.Message, state: FSMContext):
    price = float(message.text)
    await state.update_data(price=price)
    data = await state.get_data()
    await message.reply(f"Название: {data['title']}\nОписание: {data['description']}\nЦена: {price}\n\nОпубликовать?", reply_markup=confirm_keyboard())
    await AdCreation.next()


@dp.message_handler(lambda message: message.text.lower() not in ['да', 'нет'], state=AdCreation.confirm)
async def process_confirm_invalid(message: types.Message):
    return await message.reply("Пожалуйста, выберите 'Да' или 'Нет' с помощью кнопок.", reply_markup=confirm_keyboard())


@dp.message_handler(lambda message: message.text.lower() == 'да', state=AdCreation.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    message_sent = await bot.send_photo(CHANNEL_ID, photo=data['photo'], caption=f"{data['title']}\n{data['description']}\nЦена: {data['price']}")
    db.add_ad(message.from_user.id, data['title'], data['description'], data['photo'], data['price'], message_sent.message_id)
    await message.reply("Ваше объявление опубликовано!", reply_markup=main_menu_keyboard())
    await state.finish()


@dp.message_handler(lambda message: message.text.lower() == 'нет', state=AdCreation.confirm)
async def process_decline(message: types.Message, state: FSMContext):
    await message.reply("Объявление отменено.", reply_markup=main_menu_keyboard())
    await state.finish()


@dp.message_handler(lambda message: message.text == "Мои объявления")
async def my_ads(message: types.Message):
    ads = db.get_ads(message.from_user.id)
    if ads:
        for ad in ads:
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            edit_button = KeyboardButton(f"Изменить {ad[0]}")
            delete_button = KeyboardButton(f"Удалить {ad[0]}")
            keyboard.add(edit_button, delete_button)
            await bot.send_photo(message.from_user.id, photo=ad[4], caption=f"{ad[2]}\n{ad[3]}\nЦена: {ad[5]}", reply_markup=keyboard)
    else:
        await message.reply("У вас нет объявлений.")


@dp.message_handler(lambda message: message.text.startswith("Удалить"))
async def delete_ad(message: types.Message):
    ad_id = int(message.text.split()[1])
    ad = db.get_ad(ad_id)
    if ad:
        try:
            await bot.delete_message(CHANNEL_ID, ad[6])  # Удаляем из канала
        except Exception as e:
            await message.reply(f"Ошибка при удалении из канала: {str(e)}")
        db.delete_ad(ad_id)
        await message.reply("Объявление удалено.", reply_markup=main_menu_keyboard())


@dp.message_handler(lambda message: message.text.startswith("Изменить"))
async def edit_ad(message: types.Message):
    ad_id = int(message.text.split()[1])
    await AdEditing.ad_id.set()
    await dp.current_state(user=message.from_user.id).update_data(ad_id=ad_id)
    await message.reply("Что вы хотите изменить?", reply_markup=edit_choice_keyboard())


@dp.message_handler(lambda message: message.text.lower() == "название", state=AdEditing.ad_id)
async def edit_ad_title(message: types.Message, state: FSMContext):
    await AdEditing.title.set()
    await message.reply("Введите новое название объявления:")


@dp.message_handler(lambda message: message.text.lower() == "описание", state=AdEditing.ad_id)
async def edit_ad_description(message: types.Message, state: FSMContext):
    await AdEditing.description.set()
    await message.reply("Введите новое описание объявления:")


@dp.message_handler(lambda message: message.text.lower() == "фото", state=AdEditing.ad_id)
async def edit_ad_photo(message: types.Message, state: FSMContext):
    await AdEditing.photo.set()
    await message.reply("Пришлите новое фото объявления:")


@dp.message_handler(lambda message: message.text.lower() == "цена", state=AdEditing.ad_id)
async def edit_ad_price(message: types.Message, state: FSMContext):
    await AdEditing.price.set()
    await message.reply("Введите новую цену объявления:", reply_markup=cancel_keyboard())


@dp.message_handler(lambda message: not message.text.isdigit(), state=AdEditing.price)
async def process_edit_price_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Пожалуйста, введите цену числом.")


@dp.message_handler(state=AdEditing.title)
@dp.message_handler(state=AdEditing.description)
@dp.message_handler(state=AdEditing.photo)
@dp.message_handler(state=AdEditing.price)
async def process_edit(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    async with state.proxy() as data:
        if current_state == AdEditing.photo.state:
            data['photo'] = message.photo[-1].file_id
        else:
            data[current_state.split(':')[-1]] = message.text
    await AdEditing.confirm.set()
    await message.reply("Сохранить изменения?", reply_markup=confirm_keyboard())


@dp.message_handler(lambda message: message.text.lower() == 'да', state=AdEditing.confirm)
async def process_confirm_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ad_id = data['ad_id']
    title = data.get('title', db.get_ad(ad_id)[2])
    description = data.get('description', db.get_ad(ad_id)[3])
    photo = data.get('photo', db.get_ad(ad_id)[4])
    price = data.get('price', db.get_ad(ad_id)[5])

    try:
        await bot.delete_message(CHANNEL_ID, db.get_ad(ad_id)[6])  # Удаляем старое сообщение
        message_sent = await bot.send_photo(CHANNEL_ID, photo=photo, caption=f"{title}\n{description}\nЦена: {price}")
        db.update_ad(ad_id, title, description, photo, price)  # Передаем только 5 аргументов
        await message.reply("Изменения сохранены.", reply_markup=main_menu_keyboard())
    except Exception as e:
        await message.reply(f"Ошибка при изменении объявления: {str(e)}")
    await state.finish()


@dp.message_handler(lambda message: message.text.lower() == 'нет', state=AdEditing.confirm)
async def process_cancel_edit(message: types.Message, state: FSMContext):
    await message.reply("Изменение отменено.", reply_markup=main_menu_keyboard())
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
