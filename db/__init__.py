from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from db.classes import Favorites, UsersFavorites, Archive

from credentials import USER_LOGIN, USER_PASSWORD, DB_NAME, DB_PORT, DB_HOST


Base = declarative_base()
engine = create_engine(f'mysql+pymysql://{USER_LOGIN}:{USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
# Создание таблиц соответствующих классам если таблицы в базе не существуют
Base.metadata.create_all(engine)

with engine.connect() as connection:
    version = connection.execute(text("SELECT VERSION();"))
    print(version.fetchone())

Session = sessionmaker(bind=engine)
