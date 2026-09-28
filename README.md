# 🤖 Telegram AI Trading Bot (智能合約交易機器人)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Telegram API](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram)
![Bitget API](https://img.shields.io/badge/Bitget-API-000000)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-LLM-8E75B2)

---

## 💡 專案簡介
> 本專案為了解決加密貨幣合約交易操作繁瑣、用戶在移動或辦公時不便開啟交易所 APP 的痛點而開發。
> 我們結合了 **Google Gemini LLM** 的強大語意解析能力與 **Telegram Bot** 的高便利性，打造出一款能「聽懂」自然語言指令的智能交易機器人。使用者只需在對話框輸入簡單指令，系統便會自動完成 Bitget 交易所的合約下單與風控設置，實現直覺、安全、快速的交易體驗。

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

## 🛠️ 技術堆疊 (Tech Stack)
* **Backend:** Python, `python-telegram-bot (v22.0)`
* **AI Engine:** `google-generativeai`
* **Exchange API:** `Bitget API (mix/v1)`, `requests`
* **Security:** `hmac`, `hashlib`, `base64`

## 🚀 快速開始 (Quick Start)

### 1. 取得程式碼與安裝依賴
```bash
git clone [https://github.com/你的帳號/你的專案名稱.git](https://github.com/你的帳號/你的專案名稱.git)
cd 你的專案名稱
pip install -r requirements.txt
