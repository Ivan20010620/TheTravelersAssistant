from db import Session
from db.classes import Favorites, UsersFavorites, Archive
from logger import logger


def add_favorites_to_db(name, address, phones, url):
    with Session() as session:
        try:
            session.add(Favorites(name=name, address=address, phones=phones, url=url))
            session.commit()
        except Exception as e:
            logger.error(f"DB error {str(e)} for {name, address, phones, url}")
            session.rollback()


def add_matching_ids_to_user_favorites(matching_ids, user_id):
    with Session() as session:
        for favorites_id in matching_ids:
            try:
                session.add(UsersFavorites(user_id=user_id, favorites_id=favorites_id))
                session.commit()
            except Exception as e:
                logger.error(f"DB error {str(e)} for {matching_ids, user_id}")
                session.rollback()


def add_data_to_archive(user_id, favorite_id):
    with Session() as session:
        try:
            session.add(Archive(user_id=user_id, favorite_id=favorite_id))
            session.commit()
        except Exception as e:
            logger.error(f"DB error {str(e)} for {user_id, favorite_id}")
            session.rollback()


def delete_user_favorites(user_id, favorite_id):
    with Session() as session:
        try:
            # Находим все объекты для удаления
            objects_to_delete = session.query(UsersFavorites).filter_by(user_id=user_id, favorite_id=favorite_id).all()
            if objects_to_delete:
                for obj in objects_to_delete:
                    session.delete(obj)
                session.commit()
                return True
            else:
                logger.error(f"No matching records found for {user_id, favorite_id}")
                return False
        except Exception as e:
            logger.error(f"DB error {str(e)} for {user_id, favorite_id}")
            session.rollback()
            return False


def get_matching_ids(name, address):
    with Session() as session:
        # Используем query для запроса только ID, чтобы избежать извлечения всех полей
        matching_favorites = session.query(Favorites.id).filter_by(name=name, address=address).all()
        # Возвращаем список ID, извлеченных из кортежей
        return [favorite[0] for favorite in matching_favorites]


def get_data_archive_user_id(user_id, db_class):
    with Session() as session:
        # создаем объект query для извлечения объектов из таблицы Favorites, соединяя записи из Favorites и db_class
        # по id
        query = session.query(Favorites).join(db_class, Favorites.id == db_class.favorites_id)
        # возвращаем список отфильрованных по user_id объектов
        return query.filter(db_class.user_id == user_id).all()
