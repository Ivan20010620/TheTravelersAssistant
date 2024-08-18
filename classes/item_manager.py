import uuid


class Item:
    def __init__(self, data):
        self.id = uuid.uuid1()

        self.name = data['properties']['name']
        self.address = data['properties']['CompanyMetaData']['address']
        self.url = data['properties']['CompanyMetaData'].get('url', '')

        coordinates = data['geometry']['coordinates']
        self.longitude = coordinates[0]
        self.latitude = coordinates[1]
        self.distance = None

        self.phones = [phone['formatted'] for phone in data['properties']['CompanyMetaData'].get('Phones') if phone]
        self.formatted_phones = [phone['formatted'].translate(str.maketrans('', '', '-() ')) for phone in self.phones]

        self.phones_links_str = "Отсутствует"
        if self.phones:
            links = [f'<a href="tel:{phone}">{formatted_phone}</a>' for phone, formatted_phone in zip(self.phones,
                                                                                                      self.formatted_phones)]
            self.phones_links_str = ' '.join(links)

    def get_description(self):
        return (f"Расстояние: {self.distance} м\nНазвание: {self.name}\nАдрес: {self.address}\n"
                f"Телефоны: {self.phones_links_str}\n{self.url}")

    def __str__(self):
        return (f"ID объекта: {self.id}\n"
                f"Название: {self.name}\n"
                f"Адрес: {self.address}\n"
                f"Телефоны: {', '.join(self.phones)}\n"
                f"Долгота: {self.longitude}\n"
                f"Широта: {self.latitude}\n"
                f"Ссылка: {self.url}\n"
                f"Расстояние: {self.distance} м\n")
