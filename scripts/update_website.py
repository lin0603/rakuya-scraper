#!/usr/bin/env python3
"""
從 MongoDB 匯出資料並更新 GitHub Pages 網站
每次爬蟲完執行此腳本，自動將新物件同步到公開網站
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from pymongo import MongoClient
except ImportError:
    print("❌ 缺少 pymongo。請執行: pip install pymongo")
    sys.exit(1)

# ─── 設定 ──────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "")
if not MONGODB_URI:
    print("❌ 請設定環境變數 MONGODB_URI")
    sys.exit(1)

GITHUB_PAGES_REPO = os.getenv(
    "GITHUB_PAGES_REPO",
    "git@github.com:lin0603/taibao-houses.git"
)
WORK_DIR = "/tmp/taibao-houses-update"


def export_to_json():
    """從 MongoDB 匯出資料為前端需要的 JSON"""
    client = MongoClient(MONGODB_URI)
    coll = client["real_estate"]["listings"]
    
    listings = list(
        coll.find(
            {},
            {"raw_html": 0, "source_raw": 0, "meta_description": 0}
        ).sort("scraped_at", -1).limit(100)
    )
    
    output = []
    for item in listings:
        item["_id"] = str(item["_id"])
        output.append({
            "name": item.get("title", ""),
            "type": "房屋",
            "subtype": item.get("property_type", ""),
            "price_total": item.get("price_total_wan", 0),
            "price_per_ping": round(
                item.get("price_total_wan", 0) / item.get("area_total_ping", 1), 1
            ) if item.get("area_total_ping") else 0,
            "land_ping": None,
            "build_ping": item.get("area_total_ping", 0),
            "age": item.get("age_years", 0),
            "layout": f"{item.get('layout_rooms', 0)}房" if item.get("layout_rooms") else "",
            "floor": item.get("floor_total", 0),
            "station_time": None,
            "score": None,
            "url": item.get("source_url", ""),
            "tags": item.get("tags", []),
            "district": item.get("district", ""),
            "city": item.get("city", ""),
            "scraped_at": item.get("scraped_at", ""),
            "image_url": item.get("image_url", ""),  # 縮圖網址
            "analysis": item.get("analysis", {})  # 加入專業分析報告
        })
    
    return output


def update_website():
    """更新 GitHub Pages 網站"""
    print("🔄 開始更新 GitHub Pages 網站...")
    
    # 1. 匯出資料
    data = export_to_json()
    print(f"📊 從 MongoDB 讀取 {len(data)} 筆資料")
    
    # 2. clone / pull repo
    if Path(WORK_DIR).exists():
        subprocess.run(["git", "pull"], cwd=WORK_DIR, check=True, capture_output=True)
    else:
        subprocess.run(
            ["git", "clone", GITHUB_PAGES_REPO, WORK_DIR],
            check=True, capture_output=True
        )
    
    # 3. 寫入 listings.json
    json_path = os.path.join(WORK_DIR, "listings.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📝 已寫入 {json_path}")
    
    # 4. 更新 index.html（確保載入 listings.json 的程式碼存在）
    # 如果 index.html 還沒有載入邏輯，這裡會提示
    index_path = os.path.join(WORK_DIR, "index.html")
    if Path(index_path).exists():
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "loadScrapedData" not in html:
            print("⚠️ index.html 缺少 loadScrapedData 函數，請確認網站已整合樂屋網資料")
    
    # 5. git push
    subprocess.run(["git", "add", "-A"], cwd=WORK_DIR, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Auto-update: {len(data)} listings @ {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        cwd=WORK_DIR, capture_output=True
    )
    result = subprocess.run(["git", "push"], cwd=WORK_DIR, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 已成功 push 到 GitHub Pages")
        print(f"🌐 網站將在幾分鐘後更新: https://lin0603.github.io/taibao-houses/")
    else:
        print(f"⚠️ Push 可能失敗: {result.stderr}")
    
    return data


if __name__ == "__main__":
    update_website()
