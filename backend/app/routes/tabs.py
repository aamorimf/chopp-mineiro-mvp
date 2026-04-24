from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table, Tab
from app.schemas import TabCreate

router = APIRouter(prefix="/tabs", tags=["Tabs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_tab(data: TabCreate, db: Session = Depends(get_db)):
    # Verifica se a mesa existe
    table = db.query(Table).filter(Table.id == data.table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    tab = Tab(
        table_id=data.table_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
    )

    db.add(tab)
    db.commit()
    db.refresh(tab)

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "is_open": tab.is_open,
    }

@router.patch("/{tab_id}/request-close")
def request_tab_close(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    tab.is_requesting_close = True

    db.commit()
    db.refresh(tab)

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "is_open": tab.is_open,
        "is_requesting_close": tab.is_requesting_close,
    }

@router.patch("/{tab_id}/close")
def close_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(Tab).filter(Tab.id == tab_id).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Comanda não encontrada")

    if not tab.is_open:
        raise HTTPException(status_code=400, detail="Comanda já está fechada")

    tab.is_open = False
    tab.is_requesting_close = False

    db.commit()
    db.refresh(tab)

    return {
        "id": tab.id,
        "table_id": tab.table_id,
        "customer_name": tab.customer_name,
        "is_open": tab.is_open,
        "is_requesting_close": tab.is_requesting_close,
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
            "customer_phone": tab.customer_phone,
            "is_open": tab.is_open,
            "is_requesting_close": tab.is_requesting_close,
        }
        for tab in tabs
    ]

