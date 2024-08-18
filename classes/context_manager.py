from datetime import datetime
from settings import INACTIVE_CHAT_TIMEOUT


class ChatContext:
    def __init__(self, user_id=None, first_name=None, last_name=None):
        # Идентификационные данные пользователя
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name

        # Состояние поискового запроса
        self.spn = None
        self.results = None
        self.category = None

        # Состояние чата
        self.last_access_datetime = None
        self.last_callback = None

    def user_name(self):
        name = self.first_name if self.first_name else ""
        if self.last_name:
            if name:
                name += " " + self.last_name
            else:
                name = self.last_name

        return name if name else "Безымянный"

    def update_last_access_time(self):
        self.last_access_datetime = datetime.now()

    def is_expired(self):
        # вычисляем разницу между текущим временем и временем сохраненным при последнем доступе
        elapsed_time = datetime.now() - self.last_access_datetime
        # преобразуем полученный результат в секунды
        elapsed_seconds = elapsed_time.total_seconds()

        return elapsed_seconds > INACTIVE_CHAT_TIMEOUT

    def reset_query(self):
        self.spn = "1500"
        self.results = "5"
        self.category = "Отель"
        self.last_callback = None

    def __str__(self):
        properties = vars(self)
        props_str = ", ".join([f"{key}={value}" for key, value in properties.items()])
        return f"ChatContext({props_str})"


class GeneralContext:
    def __init__(self):
        self.chats = {}

    def add_chat(self, data):
        user_id = data.chat.id
        first_name = data.chat.first_name
        last_name = data.chat.last_name
        self.chats[user_id] = ChatContext(user_id=user_id, first_name=first_name, last_name=last_name)
        return self.chats[user_id]

    def get_chat(self, user_id=None, data=None):
        if data:
            user_id = data.chat.id

        chat_ctx = self.chats[user_id] if user_id in self.chats else self.add_chat(data)
        chat_ctx.update_last_access_time()
        return chat_ctx

    def remove_chat(self, user_id):
        self.chats.pop(user_id, None)
