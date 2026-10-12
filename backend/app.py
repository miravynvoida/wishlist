import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from backend.db import init_db, connection
from backend.auth import require_telegram_user, require_owner, validate_init_data

OWNER_IDS = [int(x.strip()) for x in os.getenv("TELEGRAM_OWNER_IDS", "8580512680,1973334354").split(",") if x.strip()]
app = FastAPI(title="Our Wishlist API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data"]
)

@app.on_event("startup")
def startup():
    init_db(OWNER_IDS)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/owners")
def owners():
    with connection() as conn:
        rows = conn.execute("""
            SELECT o.telegram_id AS id, o.display_name,
            COUNT(i.id) AS item_count
            FROM owners o LEFT JOIN items i ON i.owner_id=o.telegram_id
            GROUP BY o.telegram_id ORDER BY o.telegram_id
        """).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/categories/{owner_id}")
def categories(owner_id: int):
    with connection() as conn:
        owner = conn.execute("SELECT telegram_id FROM owners WHERE telegram_id=?", (owner_id,)).fetchone()
        if not owner:
            raise HTTPException(404, "Wishlist not found")
        rows = conn.execute("""
            SELECT c.id,c.owner_id,c.name,c.emoji,c.sort_order,COUNT(i.id) AS item_count
            FROM categories c LEFT JOIN items i ON i.category_id=c.id
            WHERE c.owner_id=? GROUP BY c.id ORDER BY c.sort_order,c.id
        """, (owner_id,)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/wishlist/{owner_id}")
def wishlist(owner_id: int, mode: str = Query("all", pattern="^(all|category)$"), category_id: Optional[int] = None,
             x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data")):
    viewer_id = None
    # Public visitors may view reservations; the wishlist owner must not receive
    # reservation status even in the raw API response.
    if x_telegram_init_data:
        viewer_id = validate_init_data(x_telegram_init_data)["id"]
    with connection() as conn:
        owner = conn.execute("SELECT telegram_id,display_name FROM owners WHERE telegram_id=?", (owner_id,)).fetchone()
        if not owner:
            raise HTTPException(404, "Wishlist not found")
        sql = """
          SELECT i.id,i.owner_id,i.category_id,i.title,i.description,i.url,i.price,i.image_url,
                 i.sort_order,i.created_at,i.updated_at,c.name AS category_name,c.emoji AS category_emoji,
                 CASE WHEN r.item_id IS NULL THEN 0 ELSE 1 END AS is_reserved
          FROM items i LEFT JOIN categories c ON c.id=i.category_id
          LEFT JOIN reservations r ON r.item_id=i.id
          WHERE i.owner_id=?
        """
        params = [owner_id]
        if category_id is not None:
            sql += " AND i.category_id=?"
            params.append(category_id)
        sql += " ORDER BY i.sort_order DESC,i.created_at DESC,i.id DESC"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        if viewer_id == owner_id:
            for row in rows:
                row["is_reserved"] = 0
        result = {"owner": dict(owner), "items": rows}
        return result

class ItemIn(BaseModel):
    owner_id: int
    title: str = Field(min_length=1, max_length=200)
    category_id: Optional[int] = None
    description: str = Field(default="", max_length=4000)
    url: str = Field(default="", max_length=2000)
    price: str = Field(default="", max_length=100)
    image_url: str = Field(default="", max_length=2000)

class CategoryIn(BaseModel):
    owner_id: int
    name: str = Field(min_length=1, max_length=80)
    emoji: str = Field(default="🎁", max_length=16)

def check_owner_category(conn, owner_id, category_id):
    if category_id is not None:
        row = conn.execute("SELECT id FROM categories WHERE id=? AND owner_id=?", (category_id, owner_id)).fetchone()
        if not row:
            raise HTTPException(400, "Category does not belong to this wishlist")

@app.post("/api/items")
def create_item(data: ItemIn, user=Depends(require_telegram_user)):
    require_owner(data.owner_id, user)
    with connection() as conn:
        check_owner_category(conn, data.owner_id, data.category_id)
        cur = conn.execute("""
            INSERT INTO items(owner_id,category_id,title,description,url,price,image_url)
            VALUES(?,?,?,?,?,?,?)
        """, (data.owner_id, data.category_id, data.title.strip(), data.description.strip(),
              data.url.strip(), data.price.strip(), data.image_url.strip()))
        return {"ok": True, "id": cur.lastrowid}

@app.patch("/api/items/{item_id}")
def update_item(item_id: int, data: ItemIn, user=Depends(require_telegram_user)):
    require_owner(data.owner_id, user)
    with connection() as conn:
        item = conn.execute("SELECT owner_id FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "Item not found")
        if item["owner_id"] != data.owner_id:
            raise HTTPException(403, "You can only edit your own wishlist")
        check_owner_category(conn, data.owner_id, data.category_id)
        conn.execute("""
          UPDATE items SET category_id=?,title=?,description=?,url=?,price=?,image_url=?,updated_at=CURRENT_TIMESTAMP
          WHERE id=?
        """, (data.category_id, data.title.strip(), data.description.strip(), data.url.strip(),
              data.price.strip(), data.image_url.strip(), item_id))
        return {"ok": True}

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, user=Depends(require_telegram_user)):
    with connection() as conn:
        item = conn.execute("SELECT owner_id FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "Item not found")
        require_owner(item["owner_id"], user)
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        return {"ok": True}

@app.delete("/api/wishlist/{owner_id}")
def clear_wishlist(owner_id: int, user=Depends(require_telegram_user)):
    require_owner(owner_id, user)
    with connection() as conn:
        conn.execute("DELETE FROM items WHERE owner_id=?", (owner_id,))
        return {"ok": True}

@app.post("/api/categories")
def create_category(data: CategoryIn, user=Depends(require_telegram_user)):
    require_owner(data.owner_id, user)
    with connection() as conn:
        try:
            cur = conn.execute("INSERT INTO categories(owner_id,name,emoji) VALUES(?,?,?)",
                               (data.owner_id, data.name.strip(), data.emoji.strip() or "🎁"))
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(409, "Category already exists")
            raise
        return {"ok": True, "id": cur.lastrowid}

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, user=Depends(require_telegram_user)):
    with connection() as conn:
        category = conn.execute("SELECT owner_id FROM categories WHERE id=?", (category_id,)).fetchone()
        if not category:
            raise HTTPException(404, "Category not found")
        require_owner(category["owner_id"], user)
        # Items remain in the wishlist but become uncategorized.
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
        return {"ok": True}

@app.post("/api/items/{item_id}/reserve")
def reserve_item(item_id: int, user=Depends(require_telegram_user)):
    with connection() as conn:
        item = conn.execute("SELECT owner_id FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "Item not found")
        if item["owner_id"] == user["id"]:
            raise HTTPException(400, "You cannot reserve your own wishlist item")
        try:
            conn.execute("INSERT INTO reservations(item_id,reserver_id) VALUES(?,?)", (item_id, user["id"]))
        except Exception:
            raise HTTPException(409, "This gift has already been reserved")
        return {"ok": True}

@app.delete("/api/items/{item_id}/reserve")
def cancel_reservation(item_id: int, user=Depends(require_telegram_user)):
    with connection() as conn:
        row = conn.execute("SELECT reserver_id FROM reservations WHERE item_id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Reservation not found")
        if row["reserver_id"] != user["id"]:
            raise HTTPException(403, "Only the person who reserved it can cancel")
        conn.execute("DELETE FROM reservations WHERE item_id=?", (item_id,))
        return {"ok": True}


# Bothost serves the Mini App and API on the same HTTPS domain.
# The frontend is built in the Docker image from miniapp/.
_dist = Path(os.getenv("MINIAPP_DIST", str(Path(__file__).resolve().parent.parent / "miniapp" / "dist")))
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="miniapp")
