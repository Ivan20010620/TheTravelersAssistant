import os
import re
import telebot
from telebot import types
import threading

from classes.context_manager import GeneralContext
from credentials import TOKEN
from db.classes import UsersFavorites, Archive
from db.utils import (
    add_favorites_to_db,
    add_matching_ids_to_user_favorites,
    add_data_to_archive,
    delete_user_favorites,
    get_data_archive_user_id,
    get_matching_ids,
)
from logger import logger
from settings import CHECK_EXPIRED_CHATS_INTERVAL
from utils import (
    geocode_maps_request, static_maps_request,
    get_address, get_country, get_city, get_street, get_house,
    search, format_data, extract_ids,
    parse_add_to_favorites_message,
)

SMOLENSK_LATITUDE = 54.773193
SMOLENSK_LONGITUDE = 32.044264

BUTTON_ACTIONS = ["Поделиться местоположением", "Мое местоположение Город Смоленск", "Выбрать радиус поиска",
                 "Выбрать максимальное количество объектов", "Избранное", "Архив", "Назад"]
CATEGORIES = ["Аптека", "Парковка", "Магазин", "Больница", "Шиномонтаж", "Парк", "Кафе", "Отель", "Памятник", "Клуб",
              "Достопримечательность"]
BUTTON_DISTANCES = ["500 метров", "1000 метров", "1500 метров", "В пределах города", "Назад"]

bot = telebot.TeleBot(TOKEN)
object_id = 0


def show_location_menu(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = []
    for text in BUTTON_ACTIONS:
        if text == "Поделиться местоположением":
            buttons.append(types.KeyboardButton(text=text, request_location=True))
        else:
            buttons.append(types.KeyboardButton(text=text))
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, "Поделитесь своим местоположением:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_favorites"))
def add_to_favorites_callback(call):
    chat_ctx = ctx.get_chat(data=call.message)
    name, address, phones, url = parse_add_to_favorites_message(call.message.text)

    if name and address and phones:
        add_favorites_to_db(name, address, ' '.join(phones), url)
        matching_ids = get_matching_ids(name, address)
        add_matching_ids_to_user_favorites(matching_ids, chat_ctx.user_id)

        callback_data = f"delete_one_{matching_ids}_{chat_ctx.user_id}"
        updated_button = types.InlineKeyboardButton(text="Удалить из Избранного ❤", callback_data=callback_data)
        bot.edit_message_reply_markup(
            chat_id=chat_ctx.user_id,
            message_id=call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(updated_button)
        )
    else:
        msg = "Не удалось добавить запись в Избранное. Повторите действие позже."
        logger.error(f"{msg} {name}:{address}:{phones}:{url}")
        bot.send_message(chat_ctx.user_id, msg)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_one'))
def delete_favorite_handler(call):
    chat_ctx = ctx.get_chat(data=call.message)
    data = call.data.replace("delete_one_", "").split("_")
    # TODO Сам то можешь объяснить как это работает?
    favorite_id = int(data[0][1:-1])  # Получаем favorite_id из строки вида '[65]'
    # Вызываем функцию удаления из базы данных
    if delete_user_favorites(chat_ctx.user_id, favorite_id):
        updated_button = types.InlineKeyboardButton(text="Добавить в Избранное ♡", callback_data=f"add_to_favorites")
        bot.edit_message_reply_markup(
            chat_id=chat_ctx.user_id,
            message_id=call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(updated_button)
        )
    else:
        msg = "Не удалось удалить запись из Избранного. Повторите действие позже."
        logger.error(f"{msg} {chat_ctx.user_id}:{favorite_id}")
        bot.send_message(chat_ctx.user_id, msg)


@bot.message_handler(content_types=['location'])
def location(message):
    chat_ctx = ctx.get_chat(data=message)
    if message.location is None:
        return

    lat = message.location.latitude
    lon = message.location.longitude
    data = geocode_maps_request(lat, lon)
    if not data:
        msg = "Не удалось определить Ваше местоположение. Повторите действие позже."
        logger.error(f"{msg} {chat_ctx.user_id}:{lat, lon}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    try:
        addr = get_address(data)
        msg = f"Ваше местоположение:\n{get_country(addr)}, {get_city(addr)}, {get_street(addr)}, {get_house(addr)}"
        bot.send_message(chat_ctx.user_id, msg)
    except Exception:
        msg = "Некорректный адрес. Уточните свое местоположение."
        logger.exception(f"{msg} {data}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    items = search(lon, lat, chat_ctx)
    if items is None:
        msg = "Произошла ошибка. Попробуйте повторить запрос позже."
        logger.error(f"{msg} {lon, lat, items}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    if not items:
        msg = f"{chat_ctx.category} в радиусе: {chat_ctx.spn} м не найдены."
        logger.info(f"{msg} {items}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    items = sorted(items, key=lambda item: item.distance)
    for item in items:
        inline_keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="Добавить в Избранное ♡", callback_data=f"add_to_favorites")
        inline_keyboard.add(button)

        map_url = get_map_url(item.address, lon, lat, item.longitude, item.latitude)
        msg = map_url if map_url else 'Не удалось загрузить карту.'
        bot.send_photo(chat_ctx.user_id, msg)

        bot.send_message(chat_ctx.user_id, text=item.get_description(), reply_markup=inline_keyboard, parse_mode='HTML')
        logger.info(item)


@bot.message_handler(func=lambda message: message.text == 'Избранное')
def show_favorites_command(message):
    chat_ctx = ctx.get_chat(data=message)
    data = get_data_archive_user_id(chat_ctx.user_id, UsersFavorites)
    formatted_data_list = format_data(data)
    ids = extract_ids(data)
    # Цикл по форматированным данным и id
    for formatted_data, id in zip(formatted_data_list, ids):
        # Разделяем отформатированные данные на строки
        lines = formatted_data.split("\n")
        # Флаг, указывающий, что началось новое сообщение
        new_message_started = False
        # Проходим по каждой строке отформатированных данных
        for line in lines:
            # Если строка начинается с "Название:", начинаем новое сообщение
            if line.startswith("Название:"):
                # Если предыдущее сообщение было начато, отправляем его
                if new_message_started:
                    bot.send_message(message.chat.id, current_message, reply_markup=inline_keyboard)
                # Начинаем новое сообщение с текущей строкой
                current_message = line + "\n"
                new_message_started = True
            else:
                # Добавляем текущую строку к текущему сообщению
                current_message += line + "\n"

        # Формируем инлайн-клавиатуру с кнопкой "Удалить"
        inline_keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_{id}")
        inline_keyboard.add(button)
        # Отправляем последнее сообщение после завершения цикла
        bot.send_message(message.chat.id, current_message, reply_markup=inline_keyboard)


@bot.message_handler(func=lambda message: message.text == 'Архив')
def command_show_archive(message):
    chat_ctx = ctx.get_chat(data=message)
    data = get_data_archive_user_id(chat_ctx.user_id, Archive)
    formatted_data_list = format_data(data)
    ids = extract_ids(data)
    # Цикл по форматированным данным и id
    for formatted_data, id in zip(formatted_data_list, ids):
        # Разделяем отформатированные данные на строки
        lines = formatted_data.split("\n")
        # Флаг, указывающий, что началось новое сообщение
        new_message_started = False
        # Проходим по каждой строке отформатированных данных
        for line in lines:
            # Если строка начинается с "Название:", начинаем новое сообщение
            if line.startswith("Название:"):
                # Если предыдущее сообщение было начато, отправляем его
                if new_message_started:
                    bot.send_message(message.chat.id, current_message)
                # Начинаем новое сообщение с текущей строкой
                current_message = line + "\n"
                new_message_started = True
            else:
                # Добавляем текущую строку к текущему сообщению
                current_message += line + "\n"
        # Формируем инлайн-клавиатуру с кнопкой "Удалить"
        bot.send_message(message.chat.id, current_message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_favorite_handler(call):
    chat_ctx = ctx.get_chat(data=call.message)
    bot.delete_message(chat_ctx.user_id, call.message.message_id)
    # Извлекаем favorite_id из callback_data
    favorite_id = int(call.data.replace("delete_", ""))
    # Вызываем функцию удаления из базы данных
    add_data_to_archive(chat_ctx.user_id, favorite_id)
    result = delete_user_favorites(chat_ctx.user_id, favorite_id)
    msg = "Запись успешно удалена." if result else "Ошибка при удалении записи."
    bot.send_message(chat_ctx.user_id, msg)


@bot.message_handler(func=lambda message: message.text == 'Удалить из Избранного ❤')
def show_favorites_command(message):
    chat_ctx = ctx.get_chat(data=message)
    file_name = f'favourites_{chat_ctx.user_id}.txt'
    if os.path.exists(file_name):
        os.remove(file_name)
        bot.send_message(chat_ctx.user_id, "Успешно удалено")
    else:
        bot.send_message(chat_ctx.user_id, "Ваш список избранного пуст")
    show_location_menu(message)


@bot.message_handler(func=lambda message: message.text == 'Выбрать максимальное количество объектов')
def handle_results_count(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons_texts = ["5", "10", "15"]
    buttons = [types.KeyboardButton(text=text) for text in buttons_texts]
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, "Выберете максимальное количество объектов:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text in ['5', '10', '15'])
def handle_results_count(message):
    chat_ctx = ctx.get_chat(data=message)
    chat_ctx.results = int(message.text)
    show_location_menu(message)


@bot.message_handler(func=lambda message: message.text in ['500 метров', '1000 метров', '1500 метров', 'Выбрать весь город'])
def handle_location_range(message):
    chat_ctx = ctx.get_chat(data=message)
    number = message.text.split()[0]
    chat_ctx.spn = number
    show_location_menu(message)


def create_button(category):
    return types.InlineKeyboardButton(text=category, callback_data=f"category_{category.lower()}")


@bot.message_handler(commands=['start', 'help', 'begin'])
@bot.message_handler(func=lambda message: re.match(r'^/(start|start|старт|/старт)$', message.text) or message.text.lower() in ['start', 'старт'])
def handle_full_list(message):
    chat_ctx = ctx.get_chat(data=message)
    chat_ctx.reset_query()
    buttons = [create_button(category) for category in CATEGORIES]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    bot.send_message(chat_ctx.user_id, "Выберите категорию:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def handle_category_callback(call):
    chat_ctx = ctx.get_chat(data=call.message)
    category = call.data.replace("category_", "").capitalize()
    chat_ctx.category = category
    show_location_menu(call.message)


# TODO зачем эта функция? разве нельзя добавить 'Назад' в список сообщений для handle_full_list?
@bot.message_handler(func=lambda message: message.text == 'Назад')
def handle_back(message):
    handle_full_list(message)


@bot.message_handler(func=lambda message: message.text == 'Мое местоположение Город Смоленск')
def handle_smolensk_location(message):
    chat_ctx = ctx.get_chat(data=message)
    bot.send_message(message.chat.id, "Ваше местоположение - центр города Смоленска")
    data = geocode_maps_request(SMOLENSK_LATITUDE, SMOLENSK_LONGITUDE)
    if not data:
        msg = "Не удалось определить адрес. Повторите действие позже."
        logger.error(f"{msg} {chat_ctx.user_id}:{SMOLENSK_LATITUDE, SMOLENSK_LONGITUDE}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    try:
        addr = get_address(data)
        msg = f"Ваше местоположение:\n{get_country(addr)}, {get_city(addr)}, {get_street(addr)}, {get_house(addr)}"
        bot.send_message(chat_ctx.user_id, msg)
    except Exception:
        msg = "Некорректный адрес. Уточните свое местоположение."
        logger.exception(f"{msg} {data}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    items = search(SMOLENSK_LATITUDE, SMOLENSK_LONGITUDE, chat_ctx)
    if items is None:
        msg = "Произошла ошибка. Попробуйте повторить запрос позже."
        logger.error(f"{msg} {SMOLENSK_LATITUDE, SMOLENSK_LONGITUDE, items}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    if not items:
        msg = f"{chat_ctx.category} в радиусе: {chat_ctx.spn} м не найдены."
        logger.info(f"{msg} {items}")
        bot.send_message(chat_ctx.user_id, msg)
        return

    items = sorted(items, key=lambda item: item.distance)
    for item in items:
        inline_keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="Добавить в Избранное ♡", callback_data=f"add_to_favorites")
        inline_keyboard.add(button)

        map_url = get_map_url(item.address, SMOLENSK_LATITUDE, SMOLENSK_LONGITUDE, item.longitude, item.latitude)
        msg = map_url if map_url else 'Не удалось загрузить карту.'
        bot.send_photo(chat_ctx.user_id, msg)

        bot.send_message(chat_ctx.user_id, text=item.get_description(), reply_markup=inline_keyboard, parse_mode='HTML')
        logger.info(item)


@bot.message_handler(func=lambda message: message.text == 'Выбрать радиус поиска')
def changing_spn(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(text=text) for text in BUTTON_DISTANCES]
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, "Выберите расстояние поиска", reply_markup=keyboard)


# TODO разобраться с не используемыми параметрами
def get_map_url(address, lon, lat, longitude, latitude):
    return static_maps_request(f"{longitude},{latitude}")


def say_goodbye(user_id):
    chat_ctx = ctx.get_chat(user_id=user_id)
    bot.send_message(
        chat_ctx.user_id,
        "{}, Вы долго отсутствовали и Ваша сессия истекла.\n"
        "Чтобы начать заново нажмите /start".format(chat_ctx.first_name),
        reply_markup=types.ReplyKeyboardRemove()
    )


def remove_expired_chats():
    logger.info("Ищем неактивные чаты. Всего чатов: {}".format(len(ctx.chats)))
    expired_chats = []
    for chat in ctx.chats.values():
        if chat.is_expired():
            expired_chats.append(chat.user_id)

    if expired_chats:
        logger.info("Найдено {} неактивных чатов".format(len(expired_chats)))
        for user_id in expired_chats:
            say_goodbye(user_id)
            ctx.remove_chat(user_id)

    threading.Timer(CHECK_EXPIRED_CHATS_INTERVAL, remove_expired_chats).start()


if __name__ == '__main__':
    # Инициализируем основной контекст приложения
    ctx = GeneralContext()
    threading.Timer(CHECK_EXPIRED_CHATS_INTERVAL, remove_expired_chats).start()

bot.polling(none_stop=True, interval=0)
