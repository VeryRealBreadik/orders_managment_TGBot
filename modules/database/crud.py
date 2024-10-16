from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .models import Clients, Orders


class Database:
    def __init__(self, session: Session):
        self.session = session

    #  Clients table
    def create_client(self, client_dict: dict):
        client = Clients(
            client_name=client_dict["client_name"],
            client_fullname=client_dict["client_fullname"],
            client_phone_number=client_dict["client_phone_number"]
        )
        self.session.add(client)
        self.session.commit()

    def get_client_by_id(self, client_id: int):
        return self.session.query(Clients).filter(Clients.client_id == client_id).first()

    def get_clients_by_name(self, client_name: str):
        return self.session.query(Clients).filter(Clients.client_name == client_name).all()

    def get_clients(self):
        return self.session.query(Clients).all()

    def update_client(self, client_id: int, client_dict: dict):
        client = self.get_client_by_id(client_id)
        for key, val in client_dict:
            setattr(client, key, val)
        self.session.add(client)
        self.session.commit()

    def delete_client(self, client_id: int):
        client = self.get_client_by_id(client_id)
        self.session.delete(client)
        self.session.commit()

    #  Orders table
    def create_order(self, order_dict: dict):
        order = Orders(
            client_id=order_dict["client_id"],
            order_date=order_dict["order_date"],
            order_sum=order_dict["order_sum"],
            order_payed=order_dict["order_payed"]
        )
        self.session.add(order)
        self.session.commit()

    def get_order_by_id(self, order_id: int):
        return self.session.query(Orders).filter(Orders.order_id == order_id).first()

    def get_orders_by_week(self, orders_date: datetime = datetime.now()):
        return self.session.query(Orders).filter(
            Orders.order_date.between(orders_date - timedelta(days=orders_date.weekday() + 1),
                                             orders_date + timedelta(days=7 - orders_date.weekday()))).order_by(
            Orders.client_id).all()

    def get_orders_by_client_id(self, client_id: int):
        return self.session.query(Orders).filter(Orders.client_id == client_id).order_by(
            Orders.order_date).all()

    def update_order(self, order_id: int, order_dict: dict):
        order = self.get_order_by_id(order_id)
        for key, val in order_dict:
            setattr(order, key, val)
        self.session.add(order)
        self.session.commit()

    def delete_order(self, order_id: int):
        order = self.get_order_by_id(order_id)
        self.session.delete(order)
        self.session.commit()
