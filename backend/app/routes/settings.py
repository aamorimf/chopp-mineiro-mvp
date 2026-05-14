from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SystemSettings

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    service_fee_enabled: bool | None = None
    service_fee_percentage: float | None = None
    couvert_enabled: bool | None = None
    couvert_price: float | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_settings(db: Session) -> SystemSettings:
    settings = db.query(SystemSettings).first()

    if settings:
        return settings

    settings = SystemSettings(
        service_fee_enabled=True,
        service_fee_percentage=10,
        couvert_enabled=False,
        couvert_price=0,
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return settings


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)

    return {
        "service_fee_enabled": settings.service_fee_enabled,
        "service_fee_percentage": settings.service_fee_percentage,
        "couvert_enabled": settings.couvert_enabled,
        "couvert_price": settings.couvert_price,
    }


@router.patch("/")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)

    if data.service_fee_enabled is not None:
        settings.service_fee_enabled = data.service_fee_enabled

    if data.service_fee_percentage is not None:
        settings.service_fee_percentage = data.service_fee_percentage

    if data.couvert_enabled is not None:
        settings.couvert_enabled = data.couvert_enabled

    if data.couvert_price is not None:
        settings.couvert_price = data.couvert_price

    db.commit()
    db.refresh(settings)

    return {
        "message": "Configurações atualizadas",
        "service_fee_enabled": settings.service_fee_enabled,
        "service_fee_percentage": settings.service_fee_percentage,
        "couvert_enabled": settings.couvert_enabled,
        "couvert_price": settings.couvert_price,
    }