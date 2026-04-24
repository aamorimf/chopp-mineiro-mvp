from app.database import SessionLocal
from app.models import Table, Product


def seed_data():
    db = SessionLocal()

    # Verifica se já existem mesas
    if db.query(Table).first():
        print("Seed já executado.")
        db.close()
        return

    # Criar mesas (1 a 10)
    for i in range(1, 11):
        table = Table(number=i)
        db.add(table)

    # Criar produtos iniciais
    products = [
        {"name": "Chopp 300ml", "price": 8.0},
        {"name": "Chopp 500ml", "price": 12.0},
        {"name": "Batata Frita", "price": 25.0},
        {"name": "Calabresa Acebolada", "price": 30.0},
        {"name": "Refrigerante Lata", "price": 6.0},
    ]

    for p in products:
        product = Product(name=p["name"], price=p["price"])
        db.add(product)

    db.commit()
    db.close()

    print("Seed executado com sucesso!")