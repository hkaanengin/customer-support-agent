from database import SessionLocal, Product

db = SessionLocal()
products = db.query(Product).all()

print(f"\n📦 Found {len(products)} products in database:\n")
for p in products:
    print(f"  • {p.name} - ${p.price} ({p.stock} in stock)")

db.close()