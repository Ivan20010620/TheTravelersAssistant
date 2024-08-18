import math
import re
import requests

from classes.item_manager import Item
from credentials import API_KEY_GEOCODER, API_KEY, API_KEY_MAP
from logger import logger
from settings import URL_SEARCH_MAPS, URL_GEOCODE_MAPS, URL_STATIC_MAPS, MAP_SIZE

R_CONST = 6371.0


def base_request(url, result_type="json"):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Код ошибки: {response.status_code}")
    except:
        logger.exception(f"Запрос {url} не выполнен.")
        return {}

    try:
        if result_type == "json":
            return response.json()
        if result_type == "url":
            return response.url
    except:
        logger.exception(f"Не удалось извлечь данные из ответа url={url}")
        return {}


def search_maps_request(category, lon, lat, results):
    url = URL_SEARCH_MAPS.format(category, API_KEY_GEOCODER, lon, lat, results)
    return base_request(url)


def geocode_maps_request(lon, lat):
    url = URL_GEOCODE_MAPS.format(API_KEY, lat, lon)
    return base_request(url)


def static_maps_request(point):
    url = URL_STATIC_MAPS.format(point, MAP_SIZE, point, API_KEY_MAP)
    return base_request(url, result_type="url")


def get_address(data):
    geo_object = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    return geo_object["metaDataProperty"]["GeocoderMetaData"]["Address"]


def get_city(address):
    # Обходим все компоненты адреса
    for component in address["Components"]:
        # Если тип компонента равен "locality", то это название города
        if component["kind"] == "locality":
            return component["name"]

    raise ValueError(f"Адрес {address} не содержит название города")


def get_country(address):
    return address["Components"][0]["name"]


def get_street(address):
    return address["Components"][-2]["name"]


def get_house(address):
    return address["Components"][-1]["name"]


def haversine(lon1, lat1, lon2, lat2):
    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)
    lon2 = math.radians(lon2)
    lat2 = math.radians(lat2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = round(R_CONST * c * 1000)
    return distance


def search(lon, lat, chat_ctx):
    logger.info(f"Поиск для {chat_ctx.first_name}:{chat_ctx.user_id} по условию {chat_ctx.category}:{chat_ctx.spn} м:")
    data = search_maps_request(chat_ctx.category, lon, lat, chat_ctx.results)
    if not data:
        return None

    items = []
    for obj_data in data['features']:
        item = Item(obj_data)
        item.distance = haversine(lon, lat, item.longitude, item.latitude)
        if item.distance > int(chat_ctx.spn):
            continue
        items.append(item)
    return items


def format_data(data):
    formatted_data_list = []
    for group in data:
        for item in group:
            name = item[1]
            address = item[2]
            phones = item[3].strip().split(', ') if item[3] and item[3] != 'Отсутствует' else []
            url = item[4] if len(item) >= 5 else ""
            formatted_data = f"Название: {name}\n"
            formatted_data += f"Адрес: {address}\n"
            if phones:
                formatted_data += f"Телефоны: {', '.join(phones)}\n"
            else:
                formatted_data += "Телефоны: Отсутствуют\n"
            if url:
                formatted_data += f"Ссылка: {url}\n"
            formatted_data_list.append(formatted_data)
    return formatted_data_list


def extract_ids(data):
    ids = []
    for group in data:
        for item in group:
            ids.append(item[0])  # Извлекаем id и добавляем его в список
    return ids


def parse_add_to_favorites_message(message):
    name_match = re.search(r"Название:\s*(.*)", message)
    name = name_match.group(1).strip() if name_match else ""

    address_match = re.search(r"Адрес\s*(.*)", message)
    address = address_match.group(1).strip() if address_match else ""

    phones_match = re.search(r"Телефоны:\s*(.*)", message)
    phones = phones_match.group(1).strip().split() if phones_match else []  # Телефоны разделены пробелами

    url_match = re.search(r"\s*(https?://\S+)", message)
    url = url_match.group(1).strip() if url_match else None
    return name, address, phones, url
