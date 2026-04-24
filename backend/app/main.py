from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.seed import seed_data
from app.routes import tables, products, tabs, orders

app = FastAPI(
    title="Chopp do Mineiro MVP",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(tabs.router)
app.include_router(orders.router)