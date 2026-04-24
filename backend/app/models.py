from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)

    tabs = relationship("Tab", back_populates="table")


class Tab(Base):
    __tablename__ = "tabs"

    id = Column(Integer, primary_key=True, index=True)

    table_id = Column(Integer, ForeignKey("tables.id"))

    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)

    is_open = Column(Boolean, default=True)

    table = relationship("Table", back_populates="tabs")
    orders = relationship("Order", back_populates="tab")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    tab_id = Column(Integer, ForeignKey("tabs.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    quantity = Column(Integer, default=1)

    is_delivered = Column(Boolean, default=False)

    tab = relationship("Tab", back_populates="orders")