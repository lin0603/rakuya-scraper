#!/usr/bin/env python3
"""
樂屋網爬蟲 + MongoDB 寫入腳本
繞過 Cloudflare 用 Playwright，解析房地產資料後寫入 MongoDB Atlas
"""

import os
import sys
import re
import json
from datetime import datetime

# 嘗試匯入，沒有就提示安裝
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 缺少 playwright。請執行: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError
except ImportError:
    print("❌ 缺少 pymongo。請執行: pip install pymongo")
    sys.exit(1)


# ─── 設定 ──────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "")
if not MONGODB_URI:
    print("❌ 請設定環境變數 MONGODB_URI")
    sys.exit(1)

DB_NAME = "real_estate"
COLLECTION_NAME = "listings"

# ─── MongoDB 連線 ──────────────────────────────────
def get_collection():
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    collection.create_index("source_url", unique=True)
    print(f"✅ MongoDB 連線成功 | DB: {DB_NAME} | Collection: {COLLECTION_NAME}")
    return client, collection


# ─── 解析樂屋網 ───────────────────────────────────
def parse_rakuya(page) -> dict:
    html_content = page.content()
    data = {
        "source": "rakuya",
        "source_url": page.url,
        "scraped_at": datetime.now().isoformat(),
        "raw_html": html_content,
    }

    # 方法1：從 window.tmpDataLayer 抓取
    try:
        tmp_data = page.evaluate("() => { try { return window.tmpDataLayer; } catch(e) { return null; } }")
        if tmp_data and "itemData" in tmp_data:
            item = tmp_data["itemData"]
            data["title"] = item.get("item_name", "")
            data["price_total"] = item.get("price", 0)
            data["price_total_wan"] = item.get("price", 0) / 10000
            data["area_total_ping"] = item.get("object_main_size", item.get("item_variant", 0))
            data["layout_rooms"] = item.get("bedrooms", 0)
            data["age_years"] = item.get("age", 0)
            data["floor_total"] = item.get("object_floor", 0)
            data["property_type"] = item.get("item_category5", "")
            data["building_age"] = item.get("object_type3", "")
            data["district"] = item.get("item_category2", "")
            data["city"] = item.get("item_category", "")
            data["tags"] = item.get("object_tag", "").split(",") if item.get("object_tag") else []
            data["upload_date"] = item.get("object_upload_time", "")
            data["update_date"] = item.get("object_update_time", "")
            data["item_id"] = item.get("item_id", "")
            data["source_raw"] = item
    except Exception as e:
        print(f"⚠️ tmpDataLayer 抓取失敗: {e}")

    # 方法2：從 meta description 補充
    try:
        meta_desc = page.locator('meta[property="og:description"]').first.get_attribute("content")
        if meta_desc:
            data["meta_description"] = meta_desc
            addr_match = re.search(r'位於([^，。]+)', meta_desc)
            if addr_match and "address" not in data:
                data["address"] = addr_match.group(1).strip()
    except Exception:
        pass

    return data


# ─── 主程式 ────────────────────────────────────────
def scrape_and_store(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-TW",
        )
        page = context.new_page()

        print(f"🌐 正在開啟: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

        title = page.title()
        if "Just a moment" in title:
            print("⚠️ 仍在 Cloudflare 驗證頁，再等待 10 秒...")
            page.wait_for_timeout(10000)

        print(f"📄 頁面標題: {page.title()}")
        data = parse_rakuya(page)

        screenshot_path = "/tmp/rakuya_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 截圖已存: {screenshot_path}")
        browser.close()

    # 檢查價格是否超過 500 萬
    price = data.get("price_total_wan", 0)
    if price and price > 500:
        print(f"🚫 總價 {price} 萬超過 500 萬，跳過不存")
        return data
    
    # 檢查是否為農地（純農地跳過，建地保留）
    title = data.get("title", "")
    ptype = data.get("property_type", "")
    if any(kw in title for kw in ["農地"]) or "農地" in ptype:
        print(f"🚫 農地類型，跳過不存: {title[:20]}...")
        return data
    
    client, collection = get_collection()
    try:
        result = collection.insert_one(data)
        print(f"✅ 資料已寫入 MongoDB | _id: {result.inserted_id}")
    except DuplicateKeyError:
        print("⚠️ 這個 URL 已經存在，跳過寫入")
    except Exception as e:
        print(f"❌ MongoDB 寫入失敗: {e}")
        raise
    finally:
        client.close()

    from bson import ObjectId
    summary = {k: str(v) if isinstance(v, ObjectId) else v for k, v in data.items() if k not in ("raw_html", "meta_description", "source_raw")}
    print("\n📋 解析結果摘要:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <URL>")
        sys.exit(1)
    scrape_and_store(sys.argv[1])
