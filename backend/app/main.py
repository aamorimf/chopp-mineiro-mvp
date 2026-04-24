from fastapi import FastAPI

from app.database import init_db
from app.seed import seed_data
from app.routes import tables, products

app = FastAPI(
    title="Chopp do Mineiro MVP",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()
    seed_data()


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(tables.router)
app.include_router(products.router)