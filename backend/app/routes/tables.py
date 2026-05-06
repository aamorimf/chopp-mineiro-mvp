from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table, Tab, Order, Product, TableSession
from app.schemas import TableResponse

router = APIRouter(prefix="/tables", tags=["Tables"])


class TableGroupRequest(BaseModel):
    table_ids: list[int]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_grouped_table_ids(tab: Tab) -> set[int]:
    ids = {tab.table_id}

    if tab.grouped_table_ids:
        ids.update(
            int(id.strip())
            for id in tab.grouped_table_ids.split(",")
            if id.strip().isdigit()
        )

    return ids


def serialize_grouped_table_ids(table_ids: set[int]) -> str | None:
    if len(table_ids) <= 1:
        return None

    return ",".join(str(table_id) for table_id in sorted(table_ids))


def tab_belongs_to_table(tab: Tab, table_id: int) -> bool:
    return table_id in get_grouped_table_ids(tab)


def expand_active_group_ids(seed_ids: set[int], open_tabs: list[Tab]) -> set[int]:
    group_ids = set(seed_ids)
    changed = True

    while changed:
        changed = False

        for tab in open_tabs:
            tab_table_ids = get_grouped_table_ids(tab)

            if tab_table_ids & group_ids and not tab_table_ids.issubset(group_ids):
                group_ids.update(tab_table_ids)
                changed = True

    return group_ids


def get_group_table_numbers(table_ids: set[int], db: Session) -> list[int]:
    if not table_ids:
        return []

    tables = (
        db.query(Table)
        .filter(Table.id.in_(table_ids))
        .order_by(Table.number)
        .all()
    )

    return [table.number for table in tables]


def build_group_summary(table_id: int, db: Session):
    open_tabs = db.query(Tab).filter(Tab.is_open.is_(True)).all()
    group_ids = expand_active_group_ids({table_id}, open_tabs)

    return {
        "grouped_table_ids": sorted(group_ids),
        "grouped_table_numbers": get_group_table_numbers(group_ids, db),
    }


@router.get("/", response_model=list[TableResponse])
def list_tables(db: Session = Depends(get_db)):
    return db.query(Table).order_by(Table.number).all()

def build_table_status(table: Table, db: Session):
    all_open_tabs = db.query(Tab).filter(Tab.is_open.is_(True)).all()
    open_tabs = [tab for tab in all_open_tabs if tab_belongs_to_table(tab, table.id)]
    group_summary = build_group_summary(table.id, db)

    if not open_tabs:
        if table.is_calling_waiter:
            return {
                "table_id": table.id,
                "table_number": table.number,
                "status": "red",
                "attention_type": "waiter_call",
                "reason": "Garçom solicitado",
                "open_tabs_count": 0,
                "is_calling_waiter": True,
                **group_summary,
            }

        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "white",
            "attention_type": None,
            "reason": "Mesa livre",
            "open_tabs_count": 0,
            "is_calling_waiter": False,
            **group_summary,
        }

    has_close_request = any(tab.is_requesting_close or tab.is_closing_confirmed for tab in open_tabs)
    has_waiter_call = table.is_calling_waiter or any(tab.is_calling_waiter for tab in open_tabs)

    if has_close_request:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "attention_type": "close_request",
            "reason": "Fechamento solicitado",
            "open_tabs_count": len(open_tabs),
            **group_summary,
        }

    if has_waiter_call:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "attention_type": "waiter_call",
            "reason": "Garçom solicitado",
            "open_tabs_count": len(open_tabs),
            "is_calling_waiter": True,
            **group_summary,
        }

    open_tab_ids = [tab.id for tab in open_tabs]
    has_pending_order = (
        db.query(Order)
        .filter(
            Order.tab_id.in_(open_tab_ids),
            Order.is_delivered.is_(False),
            Order.is_cancelled.is_(False),
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
            **group_summary,
        }

    return {
        "table_id": table.id,
        "table_number": table.number,
        "status": "green",
        "reason": "Comanda aberta sem pendências",
        "open_tabs_count": len(open_tabs),
        **group_summary,
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

    all_open_tabs = db.query(Tab).filter(Tab.is_open.is_(True)).all()
    open_tabs = [tab for tab in all_open_tabs if tab_belongs_to_table(tab, table_id)]

    if session_id is not None:
        open_tabs = [tab for tab in open_tabs if tab.session_id == session_id]

    result_tabs = []

    for tab in open_tabs:
        orders = (
            db.query(Order)
            .filter(Order.tab_id == tab.id, Order.is_cancelled.is_(False))
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
        **build_group_summary(table.id, db),
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
            TableSession.is_active.is_(True),
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=403, detail="Sessão inválida")

    session_tabs = (
        db.query(Tab)
        .filter(
            Tab.session_id == session.id,
            Tab.is_open.is_(True),
        )
        .all()
    )

    if session.table_id != table_id and not any(tab_belongs_to_table(tab, table_id) for tab in session_tabs):
        raise HTTPException(status_code=403, detail="Sessão não pertence a esta mesa")

    return build_table_details(table_id, db, session.id)

@router.get("/{table_id}/staff-details")
def get_table_staff_details(table_id: int, db: Session = Depends(get_db)):
    return build_table_details(table_id, db, include_session_token=True)

@router.get("/{table_id}/group")
def get_table_group(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    return build_group_summary(table_id, db)


@router.patch("/{table_id}/group")
def group_tables_from_table(table_id: int, data: TableGroupRequest, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    requested_ids = set(data.table_ids or [])
    requested_ids.add(table_id)

    if len(requested_ids) <= 1:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma mesa para agrupar")

    tables = db.query(Table).filter(Table.id.in_(requested_ids)).all()
    found_ids = {table.id for table in tables}
    missing_ids = requested_ids - found_ids

    if missing_ids:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    all_open_tabs = db.query(Tab).filter(Tab.is_open.is_(True)).all()

    if not any(tab_belongs_to_table(tab, table_id) for tab in all_open_tabs):
        raise HTTPException(status_code=400, detail="Abra uma comanda antes de agrupar mesas")

    grouped_ids = expand_active_group_ids(requested_ids, all_open_tabs)
    affected_tabs = [
        tab
        for tab in all_open_tabs
        if get_grouped_table_ids(tab) & grouped_ids
    ]

    serialized_group = serialize_grouped_table_ids(grouped_ids)

    for tab in affected_tabs:
        tab.grouped_table_ids = serialized_group

    db.commit()

    return {
        "message": "Mesas agrupadas com sucesso",
        **build_group_summary(table_id, db),
    }


@router.delete("/{table_id}/group/{member_table_id}")
def remove_table_from_group(table_id: int, member_table_id: int, db: Session = Depends(get_db)):
    if table_id == member_table_id:
        raise HTTPException(status_code=400, detail="Não é possível remover a mesa atual do grupo")

    table_ids = {table_id, member_table_id}
    tables = db.query(Table).filter(Table.id.in_(table_ids)).all()

    if len(tables) != len(table_ids):
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    all_open_tabs = db.query(Tab).filter(Tab.is_open.is_(True)).all()

    if not any(tab_belongs_to_table(tab, table_id) for tab in all_open_tabs):
        raise HTTPException(status_code=400, detail="Nenhuma comanda aberta para esta mesa")

    current_group_ids = expand_active_group_ids({table_id}, all_open_tabs)

    if member_table_id not in current_group_ids:
        raise HTTPException(status_code=400, detail="Mesa não está no grupo")

    remaining_group_ids = current_group_ids - {member_table_id}
    remaining_group = serialize_grouped_table_ids(remaining_group_ids)

    for tab in all_open_tabs:
        tab_ids = get_grouped_table_ids(tab)

        if not (tab_ids & current_group_ids):
            continue

        if tab.table_id == member_table_id:
            tab.grouped_table_ids = None
        else:
            tab.grouped_table_ids = remaining_group

    db.commit()

    return {
        "message": "Mesa removida do grupo",
        **build_group_summary(table_id, db),
    }

@router.patch("/{table_id}/call-waiter")
def call_waiter_from_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    # 🔥 verifica se existe comanda aberta
    open_tabs = db.query(Tab).filter(
        Tab.is_open.is_(True)
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
