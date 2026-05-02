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

def clear_waiter_calls_for_table_ids(table_ids: list[int], db: Session):
    tables = db.query(Table).filter(Table.id.in_(set(table_ids))).all()

    for table in tables:
        table.is_calling_waiter = False


@router.post("/")
def create_tab(data: TabCreate, db: Session = Depends(get_db)):
    # Verifica se a mesa existe
    table = db.query(Table).filter(Table.id == data.table_id).first()

    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    grouped_ids = data.grouped_table_ids or [data.table_id]

    if data.table_id not in grouped_ids:
        grouped_ids.append(data.table_id)

    # LIMPA CHAMADO SEMPRE
    clear_waiter_calls_for_table_ids(grouped_ids, db)

    tab = Tab(
        table_id=data.table_id,
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

    if not tab.is_closing_confirmed:
        raise HTTPException(status_code=400, detail="Fechamento ainda não confirmado")

    tab.is_open = False

    tab.is_calling_waiter = False
    
    table = db.query(Table).filter(Table.id == tab.table_id).first()
    if table:
        table.is_calling_waiter = False    
    
    tab.is_requesting_close = False
    tab.is_closing_confirmed = False

    db.commit()
    db.refresh(tab)

    return {"message": "Comanda encerrada"}

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