from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table, Tab, Order, Product, TableSession
from app.schemas import TableResponse

router = APIRouter(prefix="/tables", tags=["Tables"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def tab_belongs_to_table(tab: Tab, table_id: int) -> bool:
    if tab.table_id == table_id:
        return True

    if not tab.grouped_table_ids:
        return False

    grouped_ids = [
        int(id.strip())
        for id in tab.grouped_table_ids.split(",")
        if id.strip().isdigit()
    ]

    return table_id in grouped_ids


@router.get("/", response_model=list[TableResponse])
def list_tables(db: Session = Depends(get_db)):
    return db.query(Table).order_by(Table.number).all()

def build_table_status(table: Table, db: Session):
    all_open_tabs = db.query(Tab).filter(Tab.is_open == True).all()
    open_tabs = [tab for tab in all_open_tabs if tab_belongs_to_table(tab, table.id)]

    if table.is_calling_waiter:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "attention_type": "waiter_call",
            "reason": "Garçom solicitado",
            "open_tabs_count": len(open_tabs),
            "is_calling_waiter": True,
        }

    if not open_tabs:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "white",
            "attention_type": None,
            "reason": "Mesa livre",
            "open_tabs_count": 0,
            "is_calling_waiter": False,
    }

    has_close_request = any(tab.is_requesting_close for tab in open_tabs)
    has_waiter_call = table.is_calling_waiter or any(tab.is_calling_waiter for tab in open_tabs)

    if has_close_request:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "attention_type": "close_request",
            "reason": "Fechamento solicitado",
            "open_tabs_count": len(open_tabs),
        }

    if has_waiter_call:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "attention_type": "waiter_call",
            "reason": "Garçom solicitado",
            "open_tabs_count": len(open_tabs),
            "is_calling_waiter": True
}

    open_tab_ids = [tab.id for tab in open_tabs]

    has_pending_order = (
        db.query(Order)
        .filter(
            Order.tab_id.in_(open_tab_ids),
            Order.is_delivered == False,
            Order.is_cancelled == False,
        )
        .first()
        is not None
    )

    if has_pending_order:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "yellow",
            "reason": "Pedido pendente",
            "open_tabs_count": len(open_tabs),
        }

    return {
        "table_id": table.id,
        "table_number": table.number,
        "status": "green",
        "reason": "Comanda aberta sem pendências",
        "open_tabs_count": len(open_tabs),
    }

@router.get("/status/all")
def list_all_tables_status(db: Session = Depends(get_db)):
    tables = db.query(Table).order_by(Table.number).all()

    return [build_table_status(table, db) for table in tables]

@router.get("/{table_id}/status")
def get_table_status(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    return build_table_status(table, db)

@router.get("/{table_id}/details")
def get_table_details(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    return {
        "table_id": table.id,
        "table_number": table.number,
        "is_calling_waiter": False,
        "tabs": [],
    }

def build_table_details(
    table_id: int,
    db: Session,
    session_id: int | None = None,
    include_session_token: bool = False,
):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    all_open_tabs = db.query(Tab).filter(Tab.is_open == True).all()
    open_tabs = [tab for tab in all_open_tabs if tab_belongs_to_table(tab, table_id)]

    if session_id is not None:
        open_tabs = [tab for tab in open_tabs if tab.session_id == session_id]

    result_tabs = []

    for tab in open_tabs:
        orders = (
            db.query(Order)
            .filter(Order.tab_id == tab.id, Order.is_cancelled == False)
            .all()
        )

        result_orders = []

        for order in orders:
            product = db.query(Product).filter(Product.id == order.product_id).first()

            result_orders.append({
                "id": order.id,
                "product_name": product.name if product else "Produto",
                "quantity": order.quantity,
                "is_delivered": order.is_delivered,
                "price": product.price if product else 0,
            })

        session = None
        if tab.session_id:
            session = db.query(TableSession).filter(TableSession.id == tab.session_id).first()

        result_tab = {
            "tab_id": tab.id,
            "customer_name": tab.customer_name,
            "is_open": tab.is_open,
            "is_requesting_close": tab.is_requesting_close,
            "is_closing_confirmed": tab.is_closing_confirmed,
            "is_calling_waiter": tab.is_calling_waiter,
            "orders": result_orders,
            "observation": tab.observation,
            "grouped_table_ids": tab.grouped_table_ids,
        }

        if include_session_token:
            result_tab["session_token"] = session.session_token if session else None
            result_tab["session_table_id"] = session.table_id if session else tab.table_id

        result_tabs.append(result_tab)

    return {
        "table_id": table.id,
        "table_number": table.number,
        "is_calling_waiter": table.is_calling_waiter,
        "tabs": result_tabs,
    }

@router.get("/{table_id}/session-details")
def get_table_session_details(table_id: int, session_token: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    session = (
        db.query(TableSession)
        .filter(
            TableSession.session_token == session_token,
            TableSession.is_active == True,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=403, detail="Sessão inválida")

    session_tabs = (
        db.query(Tab)
        .filter(
            Tab.session_id == session.id,
            Tab.is_open == True,
        )
        .all()
    )

    if session.table_id != table_id and not any(tab_belongs_to_table(tab, table_id) for tab in session_tabs):
        raise HTTPException(status_code=403, detail="Sessão não pertence a esta mesa")

    return build_table_details(table_id, db, session.id)

@router.get("/{table_id}/staff-details")
def get_table_staff_details(table_id: int, db: Session = Depends(get_db)):
    return build_table_details(table_id, db, include_session_token=True)

@router.patch("/{table_id}/call-waiter")
def call_waiter_from_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    # 🔥 verifica se existe comanda aberta
    open_tabs = db.query(Tab).filter(
        Tab.is_open == True
    ).all()

    open_tabs_for_table = [
        tab for tab in open_tabs if tab_belongs_to_table(tab, table_id)
    ]

    if not open_tabs_for_table:
        raise HTTPException(
            status_code=400,
            detail="Não é possível chamar o garçom sem comanda aberta"
        )

    table.is_calling_waiter = True

    db.commit()
    db.refresh(table)

    return {"message": "Garçom chamado pela mesa"}


@router.patch("/{table_id}/cancel-waiter")
def cancel_waiter_from_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    table.is_calling_waiter = False

    db.commit()
    db.refresh(table)

    return {"message": "Chamado da mesa cancelado"}
