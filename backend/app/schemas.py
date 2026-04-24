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