from flask import Flask, render_template, request
from pymongo import MongoClient
import os

app = Flask(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "")
if not MONGODB_URI:
    raise ValueError("請設定環境變數 MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client["real_estate"]
collection = db["listings"]

@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    
    mongo_filter = {}
    if query:
        mongo_filter["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"city": {"$regex": query, "$options": "i"}},
            {"district": {"$regex": query, "$options": "i"}},
            {"property_type": {"$regex": query, "$options": "i"}},
            {"tags": {"$regex": query, "$options": "i"}},
        ]
    
    listings = list(collection.find(mongo_filter).sort("scraped_at", -1))
    
    total_count = len(listings)
    prices = [l.get("price_total_wan", 0) for l in listings if l.get("price_total_wan")]
    pings = [l.get("area_total_ping", 0) for l in listings if l.get("area_total_ping")]
    
    avg_price = round(sum(prices) / len(prices), 1) if prices else 0
    avg_ping = round(sum(pings) / len(pings), 1) if pings else 0
    
    ppp_list = []
    for l in listings:
        price = l.get("price_total_wan", 0)
        ping = l.get("area_total_ping", 0)
        if price and ping and ping > 0:
            ppp_list.append(price / ping)
    avg_ppp = round(sum(ppp_list) / len(ppp_list), 1) if ppp_list else 0
    
    return render_template(
        "index.html",
        listings=listings,
        total_count=total_count,
        avg_price=avg_price,
        avg_ping=avg_ping,
        avg_ppp=avg_ppp,
        query=query,
    )

@app.route("/api/listings")
def api_listings():
    listings = list(collection.find({}, {"raw_html": 0, "source_raw": 0}).sort("scraped_at", -1).limit(100))
    for l in listings:
        l["_id"] = str(l["_id"])
    return {"listings": listings, "count": len(listings)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
