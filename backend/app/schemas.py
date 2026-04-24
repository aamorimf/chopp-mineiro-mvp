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