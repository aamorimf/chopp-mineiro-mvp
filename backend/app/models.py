from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    is_calling_waiter = Column(Boolean, default=False)
    tabs = relationship("Tab", back_populates="table")


class TableSession(Base):
    __tablename__ = "table_sessions"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"))
    session_token = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

    table = relationship("Table")


class Tab(Base):
    __tablename__ = "tabs"

    id = Column(Integer, primary_key=True, index=True)

    table_id = Column(Integer, ForeignKey("tables.id"))
    session_id = Column(Integer, ForeignKey("table_sessions.id"), nullable=True)

    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    observation = Column(String, nullable=True)
    grouped_table_ids = Column(String, nullable=True)

    is_open = Column(Boolean, default=True)

    is_requesting_close = Column(Boolean, default=False)
    is_closing_confirmed = Column(Boolean, default=False)
    is_calling_waiter = Column(Boolean, default=False)

    table = relationship("Table", back_populates="tabs")
    orders = relationship("Order", back_populates="tab")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    is_cancelled = Column(Boolean, default=False)

    id = Column(Integer, primary_key=True, index=True)

    tab_id = Column(Integer, ForeignKey("tabs.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    quantity = Column(Integer, default=1)

    is_delivered = Column(Boolean, default=False)

    tab = relationship("Tab", back_populates="orders")
