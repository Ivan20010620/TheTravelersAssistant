from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base


class Favorites(Base):
    __tablename__ = 'favorites'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    phones = Column(String(255), nullable=True)
    url = Column(String(255), nullable=True)
    __table_args__ = (
        (UniqueConstraint('name', 'address', 'phones', name='_name_address_phones_uc'),)
    )


class UsersFavorites(Base):
    __tablename__ = 'users_favorites'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(512), nullable=False)
    favorites_id = Column(Integer, ForeignKey('favorites.id'))
    favorites = relationship(Favorites, backref='users_favorites')
    __table_args__ = (
        (UniqueConstraint('user_id', 'favorites_id', name='_user_favorites_uc'),)
    )


class Archive(Base):
    __tablename__ = 'archive'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(512), nullable=False)
    favorites_id = Column(Integer, ForeignKey('favorites.id'))
    favorites = relationship(Favorites, backref='archive')
    __table_args__ = (
        (UniqueConstraint('user_id', 'favorites_id', name='_user_favorites_uc'),)
    )
