from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Tab, Table
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