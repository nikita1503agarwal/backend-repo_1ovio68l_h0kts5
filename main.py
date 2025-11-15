import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="Food Brand E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Food Brand E-Commerce API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Public endpoints
@app.get("/api/products", response_model=List[Product])
def list_products(category: Optional[str] = None, featured: Optional[bool] = None, limit: int = 50):
    try:
        query = {}
        if category:
            query["category"] = category
        if featured is not None:
            query["featured"] = featured
        docs = get_documents("product", query, limit)
        # Map Mongo _id to string id and validate via Product
        products: List[Product] = []
        for d in docs:
            d.pop("_id", None)
            products.append(Product(**d))
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CartItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None

class CheckoutRequest(BaseModel):
    customer_name: str
    email: str
    address: str
    city: str
    country: str
    items: List[CartItem]

@app.post("/api/checkout")
def checkout(payload: CheckoutRequest):
    try:
        items: List[OrderItem] = []
        subtotal = 0.0
        for it in payload.items:
            items.append(OrderItem(product_id=it.product_id, title=it.title, price=it.price, quantity=it.quantity, image=it.image))
            subtotal += it.price * it.quantity
        order = Order(
            customer_name=payload.customer_name,
            email=payload.email,
            address=payload.address,
            city=payload.city,
            country=payload.country,
            items=items,
            subtotal=subtotal,
            shipping=0,
            total=subtotal,
            status="pending",
        )
        order_id = create_document("order", order)
        return {"success": True, "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Utility endpoint to seed some demo products if empty
@app.post("/api/seed")
def seed_products():
    try:
        existing = get_documents("product", {}, limit=1)
        if existing:
            return {"message": "Products already exist"}
        sample = [
            Product(title="Spicy Chili Chips", description="Crunchy chips with a fiery chili kick.", price=3.99, category="snacks", in_stock=True, image="https://images.unsplash.com/photo-1604908177073-b5c2b6ed83e6?w=800", featured=True),
            Product(title="Organic Granola", description="Honey-sweetened granola with nuts and seeds.", price=6.5, category="breakfast", in_stock=True, image="https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=800", featured=True),
            Product(title="Tomato Basil Soup", description="Slow-simmered tomato soup with fresh basil.", price=4.75, category="meals", in_stock=True, image="https://images.unsplash.com/photo-1547592166-23ac45744acd?w=800", featured=False),
            Product(title="Mango Smoothie", description="Creamy mango smoothie with yogurt.", price=5.25, category="drinks", in_stock=True, image="https://images.unsplash.com/photo-1467453678174-768ec283a940?w=800", featured=False),
        ]
        for p in sample:
            create_document("product", p)
        return {"message": "Seeded products"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
