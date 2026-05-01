from pydantic import BaseModel


class TableResponse(BaseModel):
    id: int
    number: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float


class Config:
    from_attributes = True


class TabCreate(BaseModel):
    table_id: int
    customer_name: str
    customer_phone: str | None = None


class OrderCreate(BaseModel):
    tab_id: int
    product_id: int
    quantity: int = 1


class OrderResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    is_delivered: bool

class OrderItem(BaseModel):
    product_id: int
    quantity: int


class OrderBatchCreate(BaseModel):
    tab_id: int
    items: list[OrderItem]