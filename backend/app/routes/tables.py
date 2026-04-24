from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table, Tab, Order
from app.schemas import TableResponse

router = APIRouter(prefix="/tables", tags=["Tables"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[TableResponse])
def list_tables(db: Session = Depends(get_db)):
    return db.query(Table).order_by(Table.number).all()

def build_table_status(table: Table, db: Session):
    open_tabs = (
        db.query(Tab)
        .filter(Tab.table_id == table.id, Tab.is_open == True)
        .all()
    )

    if not open_tabs:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "white",
            "reason": "Mesa livre",
            "open_tabs_count": 0,
        }

    has_close_request = any(tab.is_requesting_close for tab in open_tabs)

    if has_close_request:
        return {
            "table_id": table.id,
            "table_number": table.number,
            "status": "red",
            "reason": "Comanda solicitando fechamento",
            "open_tabs_count": len(open_tabs),
        }

    open_tab_ids = [tab.id for tab in open_tabs]

    has_pending_order = (
        db.query(Order)
        .filter(
            Order.tab_id.in_(open_tab_ids),
            Order.is_delivered == False,
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

