import time

from sqlalchemy import ForeignKey, String, Column, Integer, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Clients(Base):
    __tablename__ = "clients"

    client_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True)
    client_name: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    client_fullname: Mapped[str] = mapped_column(String(100), nullable=False)
    client_phone_number: Mapped[str] = Column(String(20))

    def __repr__(self):
        return f"{self.client_id} - {self.client_fullname} - {self.client_phone_number}"


class Orders(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("Clients.client_id"), nullable=False)
    order_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    order_sum: Mapped[float] = mapped_column(Float, nullable=False)
    order_payed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"{self.order_id} -  - {self.order_sum} {self.order_date} {self.order_payed}" #  TODO: Разобраться с форматированием вывода заказов
