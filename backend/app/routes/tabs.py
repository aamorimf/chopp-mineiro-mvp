from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table, Tab, TableSession, Order, Product
from app.schemas import TabCreate

router = APIRouter(prefix="/tabs", tags=["Tabs"])


class TableGroupRequest(BaseModel):
    table_ids: list[int]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def clear_waiter_calls_for_table_ids(table_ids: list[int], db: Session):
    tables = db.query(Table).filter(Table.id.in_(set(table_ids))).all()

    for table in tables:
        table.is_calling_waiter = False


def get_grouped_table_ids(tab: Tab) -> set[int]:
    ids = {tab.table_id}

    if tab.grouped_table_ids:
        ids.update(
            int(table_id.strip())
            for table_id in tab.grouped_table_ids.split(",")
            if table_id.strip().isdigit()
        )

    return ids


def tab_belongs_to_table(tab: Tab, table_id: int) -> bool:
    return table_id in get_grouped_table_ids(tab)


def calculate_tab_total(tab_id: int, db: Session) -> float:
    orders = (
        db.query(Order)
        .filter(
            Order.tab_id == tab_id,
            Order.is_cancelled == False
        )
        .all()
    )

    total = 0

    for order in orders:
        product = db.query(Product).filter(Product.id == order.product_id).first()
        price = product.price if product else 0
        total += price * order.quantity

    return float(total)


@router.post("/")
def create_tab(data: TabCreate, db: Session = Depends(get_db)):
    # Verifica se a mesa existe
    table = db.query(Table).filter(Table.id == data.table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    grouped_ids = data.grouped_table_ids or [data.table_id]

    if data.table_id not in grouped_ids:
        grouped_ids.append(data.table_id)

    session = (
        db.query(TableSession)
        .filter(
            TableSession.table_id == data.table_id,
            TableSession.is_active == True
        )
        .first()
    )

    if not session:
        session = TableSession(
            table_id=data.table_id,
            session_token=str(uuid4()),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # LIMPA CHAMADO SEMPRE
    clear_waiter_calls_for_table_ids(grouped_ids, db)

    tab = Tab(
        table_id=data.table_id,
        session_id=session.id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        observation=data.observation,
        grouped_table_ids=",".join(str(id) for id in sorted(set(grouped_ids))),
)

    db.add(tab)
    db.commit()
    db.refresh(tab)

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "observation": tab.observation,
        "grouped_table_ids": tab.grouped_table_ids,
        "is_open": tab.is_open,
        "session_token": session.session_token,
    }

@router.patch("/{tab_id}/request-close")
def request_tab_close(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    has_active_orders = (
        db.query(Order)
        .filter(
            Order.tab_id == tab.id,
            Order.is_cancelled == False
        )
        .first()
        is not None
    )

    if not has_active_orders:
        tab.is_open = False
        tab.is_requesting_close = False
        tab.is_closing_confirmed = False
        tab.is_calling_waiter = False

        table_ids = [tab.table_id]

        if tab.grouped_table_ids:
            table_ids.extend(
                int(table_id.strip())
                for table_id in tab.grouped_table_ids.split(",")
                if table_id.strip().isdigit()
            )

        clear_waiter_calls_for_table_ids(table_ids, db)

        if tab.session_id:
            has_open_tabs = (
                db.query(Tab)
                .filter(
                    Tab.session_id == tab.session_id,
                    Tab.id != tab.id,
                    Tab.is_open == True
                )
                .first()
            )

            if not has_open_tabs:
                session = db.query(TableSession).filter(TableSession.id == tab.session_id).first()
                if session:
                    session.is_active = False

        db.commit()
        db.refresh(tab)

        return {
            "id": tab.id,
            "table_id": tab.table_id,
            "customer_name": tab.customer_name,
            "is_open": tab.is_open,
            "is_requesting_close": tab.is_requesting_close,
            "is_calling_waiter": tab.is_calling_waiter,
            "is_closing_confirmed": tab.is_closing_confirmed,
        }

    tab.is_requesting_close = True

    db.commit()
    db.refresh(tab)

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "is_open": tab.is_open,
        "is_requesting_close": tab.is_requesting_close,
        "is_calling_waiter": tab.is_calling_waiter,
        "is_closing_confirmed": tab.is_closing_confirmed,
    }

@router.patch("/{tab_id}/close")
def close_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_closing_confirmed:
        raise HTTPException(status_code=400, detail="Fechamento ainda não confirmado")

    tab.is_open = False

    tab.is_calling_waiter = False
    
    table = db.query(Table).filter(Table.id == tab.table_id).first()
    if table:
        table.is_calling_waiter = False    
    
    tab.is_requesting_close = False
    tab.is_closing_confirmed = False

    if tab.session_id:
        has_open_tabs = (
            db.query(Tab)
            .filter(
                Tab.session_id == tab.session_id,
                Tab.is_open == True
            )
            .first()
        )

        if not has_open_tabs:
            session = db.query(TableSession).filter(TableSession.id == tab.session_id).first()
            if session:
                session.is_active = False

    db.commit()
    db.refresh(tab)

    return {"message": "Comanda encerrada"}


@router.get("/daily-summary")
def get_daily_summary(db: Session = Depends(get_db)):
    closed_tabs = db.query(Tab).filter(Tab.is_open == False).all()
    open_tabs_count = db.query(Tab).filter(Tab.is_open == True).count()
    closing_tabs_count = (
        db.query(Tab)
        .filter(
            Tab.is_open == True,
            Tab.is_closing_confirmed == True
        )
        .count()
    )

    closed_tabs_result = []
    items_by_product = {}
    total_revenue = 0

    for tab in closed_tabs:
        table = db.query(Table).filter(Table.id == tab.table_id).first()
        total_amount = calculate_tab_total(tab.id, db)
        total_revenue += total_amount

        orders = (
            db.query(Order)
            .filter(
                Order.tab_id == tab.id,
                Order.is_cancelled == False
            )
            .all()
        )

        for order in orders:
            product = db.query(Product).filter(Product.id == order.product_id).first()
            product_name = product.name if product else "Produto desconhecido"
            price = product.price if product else 0

            if order.product_id not in items_by_product:
                items_by_product[order.product_id] = {
                    "product_id": order.product_id,
                    "product_name": product_name,
                    "quantity_sold": 0,
                    "total_amount": 0,
                }

            items_by_product[order.product_id]["quantity_sold"] += order.quantity
            items_by_product[order.product_id]["total_amount"] += price * order.quantity

        closed_tabs_result.append(
            {
                "tab_id": tab.id,
                "table_id": tab.table_id,
                "table_number": table.number if table else tab.table_id,
                "customer_name": tab.customer_name,
                "total_amount": total_amount,
            }
        )

    closed_tabs_count = len(closed_tabs_result)
    average_ticket = total_revenue / closed_tabs_count if closed_tabs_count else 0
    items_sold = sorted(
        items_by_product.values(),
        key=lambda item: item["quantity_sold"],
        reverse=True
    )

    for item in items_sold:
        item["total_amount"] = float(item["total_amount"])

    return {
        "total_revenue": float(total_revenue),
        "closed_tabs_count": closed_tabs_count,
        "average_ticket": float(average_ticket),
        "open_tabs_count": open_tabs_count,
        "closing_tabs_count": closing_tabs_count,
        "closed_tabs": closed_tabs_result,
        "items_sold": items_sold,
    }


@router.get("/table/{table_id}/open")
def list_open_tabs_by_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    tabs = (
        db.query(Tab)
        .filter(Tab.table_id == table_id, Tab.is_open == True)
        .all()
    )

    return [
        {
            "id": tab.id,
            "table_id": tab.table_id,
            "customer_name": tab.customer_name,
            "is_open": tab.is_open,
            "is_requesting_close": tab.is_requesting_close,
        }
        for tab in tabs
    ]

@router.patch("/{tab_id}/cancel-close")
def cancel_tab_close(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    tab.is_requesting_close = False

    db.commit()
    db.refresh(tab)

    return {"message": "Encerramento cancelado"}

@router.patch("/{tab_id}/group-tables")
def group_tables(tab_id: int, data: TableGroupRequest, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    requested_ids = set(data.table_ids or [])

    if not requested_ids:
        raise HTTPException(status_code=400, detail="Nenhuma mesa selecionada")

    tables = db.query(Table).filter(Table.id.in_(requested_ids)).all()
    found_ids = {table.id for table in tables}
    missing_ids = requested_ids - found_ids

    if missing_ids:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    grouped_ids = get_grouped_table_ids(tab)
    new_table_ids = requested_ids - grouped_ids

    all_open_tabs = db.query(Tab).filter(Tab.is_open == True).all()

    for table in tables:
        if table.id not in new_table_ids:
            continue

        if table.is_calling_waiter:
            raise HTTPException(status_code=400, detail="Mesa não está livre")

        for open_tab in all_open_tabs:
            if open_tab.id == tab.id:
                continue

            if tab_belongs_to_table(open_tab, table.id):
                raise HTTPException(status_code=400, detail="Mesa não está livre")

    grouped_ids.update(new_table_ids)
    tab.grouped_table_ids = ",".join(str(table_id) for table_id in sorted(grouped_ids))

    db.commit()

    return {"message": "Mesas agrupadas com sucesso"}

@router.get("/{tab_id}/status")
def get_tab_status(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "is_open": tab.is_open,
        "is_requesting_close": tab.is_requesting_close,
        "is_calling_waiter": tab.is_calling_waiter,
        "is_closing_confirmed": tab.is_closing_confirmed,
    }

@router.patch("/{tab_id}/call-waiter")
def call_waiter(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    tab.is_calling_waiter = True

    db.commit()
    db.refresh(tab)

    return {"message": "Garçom chamado"}


@router.patch("/{tab_id}/cancel-waiter")
def cancel_waiter(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    tab.is_calling_waiter = False

    db.commit()
    db.refresh(tab)

    return {"message": "Chamada cancelada"}

@router.patch("/{tab_id}/confirm-close")
def confirm_close(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_requesting_close:
        raise HTTPException(status_code=400, detail="Cliente não solicitou fechamento")

    tab.is_closing_confirmed = True

    # limpa chamado
    tab.is_calling_waiter = False
    table = db.query(Table).filter(Table.id == tab.table_id).first()
    if table:
        table.is_calling_waiter = False

    db.commit()
    db.refresh(tab)

    return {"message": "Fechamento confirmado"}
