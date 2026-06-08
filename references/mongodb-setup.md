# MongoDB Atlas 設定指南

快速建立免費 MongoDB Atlas Cluster 並取得連線字串。

## 步驟 1：註冊 Atlas

1. 前往 https://www.mongodb.com/atlas
2. 點選 **Try Free**
3. 使用 Google / GitHub / Email 註冊

## 步驟 2：建立免費 Cluster

1. 選擇 **M0 (Free Tier)**
   - 512MB 儲存空間
   - 共享 CPU
   - 對於收集數十~數百筆房產資料足夠
2. 選擇 Region：**Taiwan** 或最近的（Singapore / Tokyo / Hong Kong）
3. Cluster 名稱：預設 `Cluster0` 或自訂
4. 等待建立完成（約 1-3 分鐘）

## 步驟 3：設定權限

### Database Access（資料庫使用者）
1. 左側選 **Database Access**
2. 點 **+ Add New Database User**
3. 選 **Password Authentication**
4. 輸入使用者名稱和密碼（**記住這組密碼**）
5. 角色選 **Read and Write to Any Database**
6. 點 **Add User**

### Network Access（IP 白名單）
1. 左側選 **Network Access**
2. 點 **+ Add IP Address**
3. 如果要從任何位置連線（包括你的伺服器、本機、外部服務）：
   - 點 **Allow Access from Anywhere** → 會自動填入 `0.0.0.0/0`
   - ⚠️ 開發測試可以這樣做，正式環境建議只開放特定 IP
4. 點 **Confirm**

## 步驟 4：取得連線字串

1. 回到 **Database** → 點你的 Cluster 旁邊的 **Connect**
2. 選 **Drivers**
3. 選 **Python** → **3.12 or later**
4. 複製連線字串，格式如下：

```
mongodb+srv://<使用者名稱>:<密碼>@<cluster名稱>.xxxxx.mongodb.net/?appName=<app名稱>
```

**重要：**
- 把 `<db_password>` 替換成你的實際密碼（去掉 `<>`）
- 把 `<使用者名稱>` 替換成你的實際使用者名稱

## 步驟 5：設定環境變數

在執行爬蟲或 Flask 網站前，設定環境變數：

```bash
export MONGODB_URI="mongodb+srv://你的使用者名稱:你的密碼@你的cluster.mongodb.net/?appName=你的App名稱"
```

或寫入 `~/.bashrc` / `~/.zshrc`：
```bash
echo 'export MONGODB_URI="你的連線字串"' >> ~/.bashrc
source ~/.bashrc
```

## 步驟 6：測試連線

```bash
python3 -c "
from pymongo import MongoClient
import os
uri = os.getenv('MONGODB_URI')
client = MongoClient(uri)
client.admin.command('ping')
print('✅ MongoDB Atlas 連線成功')
"
```

## 疑難排解

### DNS 查詢失敗（NXDOMAIN）
- 確認 Cluster 已建立完成（狀態顯示為綠色勾勾）
- DNS 傳播可能需要 1-5 分鐘
- 檢查連線字串中的 cluster 名稱是否正確（不要手打，直接從 Atlas 複製）

### Authentication Failed
- 確認使用者名稱和密碼正確（注意大小寫）
- 確認密碼中沒有特殊字元未正確 URL encode（Atlas 產生的連線字串通常會自動處理）

### Connection Timeout
- 確認 Network Access 中已加入你的 IP
- 如果在公司/學校網路，防火牆可能擋住 27017 port
- 嘗試使用 `0.0.0.0/0` 開放所有 IP 測試

## 資料庫架構

本技能預設使用以下架構：

| 層級 | 名稱 | 說明 |
|---|---|---|
| Database | `real_estate` | 房地產資料庫 |
| Collection | `listings` | 物件清單 |
| Index | `source_url` (unique) | 防止重複寫入同一連結 |

不需要手動建立 Database 或 Collection，Python 腳本會自動建立。
