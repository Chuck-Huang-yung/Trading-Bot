# 🤖 Telegram AI Trading Bot (智能合約交易機器人)
**(Telegram AI Crypto Trading Bot)**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Telegram API](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram)
![Bitget API](https://img.shields.io/badge/Bitget-API-000000)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-LLM-8E75B2)

---

## 💡 專案簡介
> 本專案為了解決加密貨幣合約交易操作繁瑣、用戶在移動或辦公時不便開啟交易所 APP 的痛點而開發。
> 我們結合了 **Google Gemini LLM** 的強大語意解析能力與 **Telegram Bot** 的高便利性，打造出一款能「聽懂」自然語言指令的智能交易機器人。使用者只需在對話框輸入簡單指令，系統便會自動完成 Bitget 交易所的合約下單與風控設置，實現直覺、安全、快速的交易體驗。

---

## 🖥️ 實際操作畫面 - 智能下單與資產查詢

<img width="905" height="680" alt="image" src="https://github.com/user-attachments/assets/24b4c732-302f-4759-887a-87cecd4e038e" />

---

## ✨ 核心功能 (Core Features)

### 1. 🤖 智能語意下單 (NLP Trading)
- 採用 **Google Gemini (gemini-1.5-pro-latest)** 模型。
- 將自然語言指令（如：`btc limit 106000 3u 50x sl100000`）解析為標準 JSON，支援多空判斷、市價/限價單、保證金金額與止盈止損設置。
- 具備 Symbol 正規化功能，自動補齊 `USDT_UMCBL` 等合約後綴格式。

### 2. ⚡ 完整的交易操作 (Trade Execution)
- 透過 **Bitget U本位合約 API** 進行操作，並採用 `HMAC-SHA256` 進行安全的簽名驗證。
- 支援動態槓桿設置，以及精準的「全部平倉 / 部分平倉」功能。

### 3. 📊 即時資產與持倉查詢 (Portfolio Monitoring)
- 內建持久化選單（ReplyKeyboardMarkup），一鍵查詢：
  - **💰 總資產估值**（總權益、可用餘額、已用保證金）。
  - **📋 詳細持倉資訊**（開倉價、未實現/已實現盈虧、標記價格、保證金模式）。
  - **📈 即時幣價查詢**（支援 `/price BTC` 指令）。

### 4. 🛡️ 智能風控與防呆機制 (Risk Management)
- **逐倉強平價保護：** 系統會自動計算逐倉模式下的預估強平價（Liquidation Price），若用戶設置的止損價超出合理範圍，機器人將拒絕下單並發出警告，避免無效掛單。
- **安全數值轉換：** 嚴謹處理 `float` 與 `int` 轉換，並防禦因 LLM 幻覺（如回傳 `null` 或異常格式）導致的系統崩潰。

---

## 🛠️ 技術堆疊 (Tech Stack)
* **Backend:** Python, `python-telegram-bot (v22.0)`
* **AI Engine:** `google-generativeai`
* **Exchange API:** `Bitget API (mix/v1)`, `requests`
* **Security:** `hmac`, `hashlib`, `base64`

---

## 📁 專案核心目錄導覽 (Directory Structure)

```text
Telegram-Trading-Bot/
├── main.py                 # 主程式 (包含 Telegram 路由、Bitget API 呼叫、AI 解析邏輯)
├── requirements.txt        # 系統依賴環境設定檔
├── env_example             # 環境變數範本 (Telegram Token, API Keys)
└── README.md               # 專案說明文件
```

---

## 🚀 快速開始 (Quick Start)

### 1. 取得程式碼與安裝依賴
```bash
git clone https://github.com/Chuck-Huang-yung/Trading-Bot.git
cd Trading-Bot
pip install -r requirements.txt
```

### 2. 環境變數設定 (Environment Variables)
請複製目錄下的 `env_example` 檔案，並將其重新命名為 `.env`，然後填入以下必備的金鑰：
```env
TELEGRAM_TOKEN=你的Telegram機器人Token
BITGET_API_KEY=你的Bitget_API_KEY
BITGET_API_SECRET=你的Bitget_API_SECRET
BITGET_PASSPHRASE=你的Bitget_Passphrase
GEMINI_API_KEY=你的Gemini_API_KEY
```

### 3. 啟動機器人
```bash
python main.py
```
(啟動成功後，終端機會顯示 Bot is running...)

---

## 📝 實用自然語言指令範例 (Examples)
* **即時查價：** /price BTC
* **市價開多：** sol多 10u 50x tp185 sl160 cross (全倉 50 倍，保證金 10 USDT)
* **Exchange API:** btc limit 106000 3u 50x sl110000 isolated (逐倉 50 倍限價單)
* **Security:** sol多 平倉5u (平掉保證金價值為 5U 的倉位)

---

## ⚠️ 免責聲明
> 本專案僅供程式語言學習與技術展示交流之用。加密貨幣合約交易具有極高風險，使用本機器人進行實盤交易前，請確保您充分了解交易所 API 規則及自身風險承受能力，開發者對任何交易損失概不負責。
