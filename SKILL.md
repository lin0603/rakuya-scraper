---
name: rakuya-scraper
description: "自動爬取樂屋網房地產物件、解析結構化資料、寫入 MongoDB Atlas，並提供 Flask 比價儀表板。Use when: (1) 群組中收到樂屋網連結需要自動爬取並結構化，(2) 需要建立房地產物件 MongoDB 資料庫，(3) 需要啟動本地 Flask 儀表板查看或搜尋已收集的物件，(4) 需要解析樂屋網 HTML 或 tmpDataLayer 提取房產欄位。"
---

# Rakuya Scraper

自動爬取樂屋網房地產物件並建立比價資料庫。

## Core Capabilities

### 1. 爬取樂屋網物件

樂屋網有 Cloudflare 保護，使用 Playwright 繞過。核心技巧：頁面內的 `window.tmpDataLayer` 包含完整結構化 JSON，優先從這裡抓取，比 DOM 選擇器穩定。

```python
# 關鍵抓取邏輯
page.goto(url, wait_until="domcontentloaded", timeout=60000)
page.wait_for_timeout(8000)  # 等 Cloudflare JS 跑完
item = page.evaluate("() => window.tmpDataLayer?.itemData")
```

執行腳本：`scripts/scrape_rakuya.py <URL>`

**腳本會做：**
- 用 Playwright 開瀏覽器繞過 Cloudflare
- 從 `tmpDataLayer.itemData` 提取結構化資料
- 備份完整 HTML 到 `/tmp/rakuya_page.html`
- 抓取 `og:image` 縮圖
- 寫入 MongoDB Atlas（`real_estate.listings`）
- 建立 `source_url` 唯一索引避免重複
- **🚫 總價超過 500 萬自動跳過不存**

**抓到的欄位：**
- `title`, `price_total_wan`, `area_total_ping`
- `layout_rooms`, `age_years`, `floor_total`
- `property_type`, `building_age`, `district`, `city`
- `tags` (列表), `upload_date`, `update_date`
- `source_url`, `scraped_at`, `raw_html`, `source_raw`

### 2. MongoDB Atlas 設定

見 `references/mongodb-setup.md` 取得 Atlas 免費 Cluster 建置與連線字串取得步驟。

連線字串格式：
```
mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?appName=<app>
```

**必要套件：**
```bash
pip install playwright pymongo[srv]
playwright install chromium
```

### 3. Flask 比價儀表板

執行：`scripts/app.py`

**功能：**
- `/` — 物件列表表格，支援搜尋（標題、城市、區域、類型、標籤）
- `/api/listings` — JSON API，回傳最新 100 筆
- 統計面板：總筆數、平均總價、平均坪數、平均單價/坪

**啟動後網址：** `http://<本機IP>:5000/`

### 4. 自動更新 GitHub Pages 網站

當群組貼樂屋網連結時，完整自動化流程：

```
群組貼連結 → 爬蟲 → MongoDB → 匯出 JSON → push 到 GitHub Pages repo → 網站自動更新
```

**執行：** `scripts/update_website.py`

**流程：**
1. 從 MongoDB `real_estate.listings` 讀取最新資料
2. 轉換成前端需要的格式（統一欄位名稱）
3. 寫入 `listings.json`
4. 更新 `index.html`（載入 `listings.json`）
5. `git push` 到 GitHub Pages repo
6. 網站幾分鐘後自動顯示新物件

**網站顯示：**
- 手動新增的物件（localStorage）+ 爬取的物件（`listings.json`）混合顯示
- 爬取物件標示 `🤖 樂屋網` 標籤區分
- 支援排序（價格、單價、評分）

### 5. 與 OpenClaw 整合

在群組中偵測樂屋網連結時：
1. 執行 `scrape_rakuya.py <URL>` 爬取
2. 回傳解析摘要給群組
3. 執行 `update_website.py` 更新網站
4. 回傳網站連結給群組

## 欄位對照表

| tmpDataLayer 欄位 | 輸出欄位 | 說明 |
|---|---|---|
| `item_name` | `title` | 標題 |
| `price` | `price_total_wan` | 總價（自動除 10000 轉成萬） |
| `object_main_size` | `area_total_ping` | 主建物坪數 |
| `bedrooms` | `layout_rooms` | 房數 |
| `age` | `age_years` | 屋齡 |
| `object_floor` | `floor_total` | 樓層數 |
| `item_category5` | `property_type` | 房屋類型（透天厝/公寓 etc） |
| `item_category` | `city` | 縣市 |
| `item_category2` | `district` | 行政區 |
| `object_tag` | `tags` | 標籤（逗號分割轉列表） |
| `object_upload_time` | `upload_date` | 上傳日期 |

## Resources

- `scripts/scrape_rakuya.py` — 爬蟲腳本
- `scripts/app.py` — Flask 儀表板（本地使用）
- `scripts/update_website.py` — 自動更新 GitHub Pages 網站
- `assets/website-template.html` — GitHub Pages 前端模板（含樂屋網資料整合）
- `references/mongodb-setup.md` — MongoDB Atlas 建置指南
