from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Order, Product, Tab
from app.schemas import OrderCreate

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == data.tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    product = db.query(Product).filter(Product.id == data.product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

    order = Order(
        tab_id=data.tab_id,
        product_id=data.product_id,
        quantity=data.quantity,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "tab_id": order.tab_id,
        "product_id": order.product_id,
        "product_name": product.name,
        "quantity": order.quantity,
        "is_delivered": order.is_delivered,
    }

@router.get("/tab/{tab_id}", response_model=list[dict])
def list_orders_by_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    orders = db.query(Order).filter(Order.tab_id == tab_id).all()

    result = []

    for order in orders:
        product = db.query(Product).filter(Product.id == order.product_id).first()

        result.append(
            {
                "id": order.id,
                "product_id": order.product_id,
                "product_name": product.name if product else "Produto desconhecido",
                "quantity": order.quantity,
                "is_delivered": order.is_delivered,
            }
        )

    return result