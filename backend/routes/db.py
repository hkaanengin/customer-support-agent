from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy import or_

router = APIRouter(prefix="/db", tags=["db"])


def _safe_import_db():
    try:
        from database.database import SessionLocal, Product  # type: ignore
        return SessionLocal, Product
    except Exception as e:  # pragma: no cover
        import sys, os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if base_dir not in sys.path:
            sys.path.append(base_dir)
        from database.database import SessionLocal, Product  # type: ignore
        return SessionLocal, Product


@router.get("/products")
def list_products(q: str = "", limit: int = 20) -> Dict[str, Any]:
    SessionLocal, Product = _safe_import_db()
    db = SessionLocal()
    try:
        query = db.query(Product)
        if q:
            raw = q.strip()
            # tokenize on spaces and punctuation
            import re
            tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", raw.lower()) if t]
            # simple synonyms/normalization
            expanded = []
            for t in tokens:
                if t in ("tshirt", "tee", "t", "tshirts"):
                    expanded.extend(["tshirt", "t-shirt", "tee"])
                else:
                    expanded.append(t)
            # build ILIKE patterns for postgres, case-insensitive
            likes = []
            for t in set(expanded):
                pat = f"%{t}%"
                likes.append(Product.name.ilike(pat))
                likes.append(Product.category.ilike(pat))
                likes.append(Product.description.ilike(pat))
            query = query.filter(or_(*likes))
        items = query.limit(limit).all()
        return {
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": p.price,
                    "description": p.description,
                    "stock": p.stock,
                }
                for p in items
            ]
        }
    finally:
        db.close()


@router.post("/products/{product_id}")
def update_product(product_id: int, body: Dict[str, Any]) -> Dict[str, Any]:
    SessionLocal, Product = _safe_import_db()
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p:
            raise HTTPException(status_code=404, detail="Product not found")
        for field in ["name", "category", "price", "description", "stock"]:
            if field in body:
                setattr(p, field, body[field])
        db.add(p)
        db.commit()
        db.refresh(p)
        return {"status": "ok", "item": {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "price": p.price,
            "description": p.description,
            "stock": p.stock,
        }}
    finally:
        db.close()


@router.get("/health")
def db_health() -> Dict[str, Any]:
    """Quick DB connectivity check."""
    SessionLocal, _ = _safe_import_db()
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()


@router.get("/debug/sample")
def debug_sample(limit: int = 10) -> Dict[str, Any]:
    """Return first N products to verify data visibility."""
    SessionLocal, Product = _safe_import_db()
    db = SessionLocal()
    try:
        items = db.query(Product).limit(limit).all()
        return {
            "count": len(items),
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": p.price,
                    "stock": p.stock,
                }
                for p in items
            ],
        }
    finally:
        db.close()


@router.get("/debug/search")
def debug_search(q: str = "", limit: int = 10) -> Dict[str, Any]:
    """Show how the query is tokenized/expanded and what matches."""
    SessionLocal, Product = _safe_import_db()
    db = SessionLocal()
    try:
        import re
        tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", q.lower()) if t]
        expanded = []
        for t in tokens:
            if t in ("tshirt", "tee", "t", "tshirts"):
                expanded.extend(["tshirt", "t-shirt", "tee"])
            else:
                expanded.append(t)
        likes = []
        for t in sorted(set(expanded)):
            pat = f"%{t}%"
            likes.append(Product.name.ilike(pat))
            likes.append(Product.category.ilike(pat))
            likes.append(Product.description.ilike(pat))
        query = db.query(Product)
        if likes:
            query = query.filter(or_(*likes))
        items = query.limit(limit).all()
        return {
            "tokens": tokens,
            "expanded": sorted(set(expanded)),
            "match_count": len(items),
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "price": p.price,
                }
                for p in items
            ],
        }
    finally:
        db.close()


@router.get("/meta")
def db_meta() -> Dict[str, Any]:
    """Return safe DB connection metadata (no passwords)."""
    try:
        # Import engine from database module
        from database.database import engine  # type: ignore
        url = engine.url
        return {
            "driver": url.drivername,
            "host": url.host,
            "port": url.port,
            "database": url.database,
            "username": url.username,
        }
    except Exception as e:
        return {"error": str(e)}


