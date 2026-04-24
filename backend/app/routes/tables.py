from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Table
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