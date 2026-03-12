# Markdown Editor

桌面版 Markdown 編輯器，使用 **FastAPI (Python)** + **Vue.js (mavonEditor)** + **Electron** 建構，  
打包後無需安裝 Python 或 Node.js 即可運行。

---

## 功能特色

- **即時預覽** — 左右分欄編輯與預覽同步捲動
- **多種檢視模式** — 分割檢視 / 純編輯 / 純預覽，按 `F9` 循環切換
- **閱讀模式** — `F11` 全螢幕預覽
- **導覽面板** — `F8` 開啟文件大綱目錄
- **匯出 PDF** — 支援中文（內建 Noto Sans TC 字體）、PDF 書籤大綱導覽
- **匯出 HTML** — 產生含側邊導覽列的獨立 HTML 文件
- **多國語系** — 繁體中文 / English，從 View 選單即時切換
- **檔案關聯** — 安裝後可設為 `.md` 預設開啟程式
- **隨機 Port** — 後端綁定 `127.0.0.1` 隨機可用 port，不會衝突且外部無法存取

---

## 專案結構

```
MarkdownEditor/
├── backend/          # Python FastAPI 後端
│   ├── app/
│   │   ├── main.py           # FastAPI 應用程式
│   │   ├── routes/
│   │   │   ├── files.py      # 檔案讀寫 API
│   │   │   ├── export.py     # 匯出 PDF / HTML API
│   │   │   └── assets/
│   │   │       └── fonts/
│   │   │           └── NotoSansTC-Regular.ttf  # 中文字體（打包進 exe）
│   │   └── schemas/
│   │       └── file_schema.py
│   ├── server.py             # uvicorn 啟動入口
│   ├── server.spec           # PyInstaller 打包設定
│   └── requirements.txt
│
├── frontend/         # Vue.js 前端 (mavonEditor)
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── components/
│   │   │   └── MdEditor.vue  # 主編輯器元件
│   │   ├── api/
│   │   │   └── fileApi.js    # 前端 API 呼叫
│   │   └── i18n/
│   │       └── index.js      # 多國語系設定 (en / zh-TW)
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   ├── vue.config.js
│   └── babel.config.js
│
├── electron/         # Electron 殼層 + 打包設定
│   ├── main.js               # Electron 主程序
│   ├── preload.js            # Context Bridge
│   └── package.json          # electron-builder 設定
│
├── scripts/          # 建置腳本
│   ├── build_frontend.bat
│   ├── build_backend.bat
│   ├── build_electron.bat
│   └── build_all.bat         # 一鍵全部建置
│
└── dist_electron/    # (建置產出) 安裝檔
```

---

## 開發環境需求

| 工具      | 版本建議       |
|-----------|---------------|
| Python    | 3.10+         |
| Node.js   | 18+           |
| npm       | 9+            |

> **注意**：上述工具僅開發/打包時需要，最終 EXE 不需要。

---

## 開發模式

### 1. 啟動後端

```bash
cd backend
pip install -r requirements.txt
python server.py --port 48765
```

### 2. 啟動前端（另一個終端）

```bash
cd frontend
npm install
npm run serve
```

前端 dev server 跑在 `http://localhost:8080`，API 請求自動 proxy 到後端 `48765`。

### 3. 用 Electron 啟動（另一個終端）

```bash
cd electron
npm install
npm start
```

---

## 一鍵打包

```bash
scripts\build_all.bat
```

依序執行：
1. **build_frontend** — `npm run build` → `frontend/dist/`
2. **build_backend** — 複製前端靜態檔 → PyInstaller 打包 → `backend/dist/server/`
3. **build_electron** — electron-builder 打包 → `dist_electron/`

產出的安裝檔在 `dist_electron/` 資料夾中。

---

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/health` | GET | 健康檢查 |
| `/api/file?path=` | GET | 讀取 `.md` 檔案 |
| `/api/file` | POST | 寫入 `.md` 檔案 |
| `/api/export/pdf` | POST | 匯出 PDF（支援中文、書籤大綱） |
| `/api/export/html` | POST | 匯出 HTML（含側邊導覽列） |

---

## 匯出功能

### PDF 匯出
- 使用 **fpdf2** 自建 PDF 渲染器
- 內建 **Noto Sans TC** 字體，完整支援中文顯示
- 支援：標題 (h1–h6)、段落、程式碼區塊、有序/無序清單、引用區塊、表格、分隔線
- 自動產生 **PDF 書籤大綱**，可在 PDF 閱讀器的書籤面板中導覽

### HTML 匯出
- 產生獨立的 HTML 文件，無需額外依賴即可開啟
- 左側固定導覽列（自動產生目錄）
- 現代化 CSS 樣式（深色程式碼區塊、響應式表格、引用區塊樣式等）

---

## 設為 .md 預設開啟程式

安裝後，在 Windows 設定中：

1. **設定 → 應用程式 → 預設應用程式**
2. 搜尋 `.md`
3. 選擇 **Markdown Editor**

或直接對任意 `.md` 檔案右鍵 → **開啟檔案** → **選擇其他應用程式** → 勾選「一律使用此應用程式」。

electron-builder 的 NSIS 安裝程式已自動註冊 `.md` 檔案關聯。

---

## 快捷鍵

| 快捷鍵           | 功能                  |
|-----------------|-----------------------|
| Ctrl + N        | 新增檔案               |
| Ctrl + O        | 開啟檔案               |
| Ctrl + S        | 儲存                   |
| Ctrl + Shift + S | 另存新檔              |
| F8              | 切換導覽面板            |
| F9              | 切換檢視模式            |
| F10             | 切換選單列              |
| F11             | 切換閱讀模式（全螢幕）    |
| Escape          | 關閉選單               |
