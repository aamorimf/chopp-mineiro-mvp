from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Order, Product, Tab, Table
from app.schemas import OrderCreate, OrderBatchCreate


router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def clear_waiter_calls_for_tab(tab: Tab, db: Session):
    tab.is_calling_waiter = False

    table_ids = [tab.table_id]

    if tab.grouped_table_ids:
        table_ids.extend(
            int(id.strip())
            for id in tab.grouped_table_ids.split(",")
            if id.strip().isdigit()
        )

    tables = db.query(Table).filter(Table.id.in_(set(table_ids))).all()

    for table in tables:
        table.is_calling_waiter = False


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

    clear_waiter_calls_for_tab(tab, db)


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

@router.get("/tab/{tab_id}")
def list_orders_by_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    orders = (
        db.query(Order)
        .filter(Order.tab_id == tab_id, Order.is_cancelled == False)
        .all()
    )

    result = []
    total = 0

    for order in orders:
        product = db.query(Product).filter(Product.id == order.product_id).first()

        price = product.price if product else 0
        subtotal = price * order.quantity

        total += subtotal

        result.append(
            {
                "id": order.id,
                "product_id": order.product_id,
                "product_name": product.name if product else "Produto desconhecido",
                "quantity": order.quantity,
                "is_delivered": order.is_delivered,
                "price": price,
                "subtotal": subtotal
            }
        )

    return {
    "orders": result,
    "total": total,
    "is_requesting_close": tab.is_requesting_close,
    "is_closing_confirmed": tab.is_closing_confirmed
}

@router.patch("/{order_id}/deliver")
def mark_order_as_delivered(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    order.is_delivered = True
    tab = db.query(Tab).filter(Tab.id == order.tab_id).first()
    if tab:
        clear_waiter_calls_for_tab(tab, db)

    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "tab_id": order.tab_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "is_delivered": order.is_delivered,
    }

@router.patch("/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if order.is_delivered:
        raise HTTPException(
            status_code=400,
            detail="Pedido entregue não pode ser cancelado"
        )

    order.is_cancelled = True

    tab = db.query(Tab).filter(Tab.id == order.tab_id).first()
    if tab:
        clear_waiter_calls_for_tab(tab, db)

    db.commit()
    db.refresh(order)

    return {"message": "Pedido cancelado"}

@router.post("/batch")
def create_order_batch(data: OrderBatchCreate, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == data.tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda fechada")
        clear_waiter_calls_for_tab(tab, db)
        tab.is_calling_waiter = False

        table = db.query(Table).filter(Table.id == tab.table_id).first()
        if table:
            table.is_calling_waiter = False

    created_orders = []

    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Produto {item.product_id} não encontrado")

        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantidade inválida")

        order = Order(
            tab_id=data.tab_id,
            product_id=item.product_id,
            quantity=item.quantity
        )

        db.add(order)
        created_orders.append(order)

    db.commit()

    return {"message": "Pedidos criados com sucesso"}