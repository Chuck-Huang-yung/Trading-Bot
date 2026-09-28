import os
import json
import requests
import time
import hmac
import hashlib
import base64
import re
import asyncio


import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any


from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 讀取 .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BITGET_API_KEY = os.getenv("BITGET_API_KEY")
BITGET_API_SECRET = os.getenv("BITGET_API_SECRET")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE")

# ====== Gemini 初始化 ======
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-pro-latest')

# ========== Bitget API 工具 ==========

#取得當前時間戳記(Bitget api需使用)
def get_timestamp():
    return str(int(time.time() * 1000))

#簽名產生(Bitget規範)
def bitget_sign(timestamp, method, request_path, body):
    prehash = f"{timestamp}{method.upper()}{request_path}{body or ''}"
    sign = hmac.new(BITGET_API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    return base64.b64encode(sign).decode()

#取得當前價格
def get_bitget_price(symbol):
    """
    symbol: 例如 BTCUSDT_UMCBL
    回傳現價(float)，失敗則回傳 None
    """
    try:
        url = f"https://api.bitget.com/api/mix/v1/market/ticker?symbol={symbol}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        return float(data['data']['last'])
    except Exception as e:
        return None

#查詢全部持倉
def get_all_positions():
    try:
        timestamp = get_timestamp()
        method = "GET"
        request_path = "/api/mix/v1/position/allPosition"
        query = "?productType=umcbl"
        pre_hash = f"{timestamp}{method}{request_path}{query}"
        signature = hmac.new(BITGET_API_SECRET.encode('utf-8'), pre_hash.encode('utf-8'), digestmod=hashlib.sha256)
        signature = base64.b64encode(signature.digest()).decode()
        headers = {
            "ACCESS-KEY": BITGET_API_KEY,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": BITGET_PASSPHRASE
        }
        url = f"https://api.bitget.com{request_path}{query}"
        res = requests.get(url, headers=headers, timeout=5)
        return res.json()
    except Exception as e:
        return {"code": "error", "msg": f"查詢持倉失敗: {str(e)}"}


#智慧下單
def bitget_place_order(order_dict):
    url = f"https://api.bitget.com/api/mix/v1/order/placeOrder"
    timestamp = str(int(time.time() * 1000))
    method = "POST"
    request_path = "/api/mix/v1/order/placeOrder"
    body = json.dumps(order_dict)
    sign = bitget_sign(timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, data=body)
    return resp.json()

#設置槓桿
def set_leverage(symbol: str, margin_coin: str, leverage: int, hold_side: str) -> Dict[str, Any]:
    """
    設置 Bitget 合約槓桿
    參數:
        symbol: 交易對，例如 'BTCUSDT_UMCBL'
        margin_coin: 保證金幣種，例如 'USDT'
        leverage: 槓桿倍數，例如 10
        hold_side: 持倉方向，'long' 或 'short'
    回傳:
        API 回應結果 (JSON 格式)
    """
    if leverage < 1:
        raise ValueError(f"槓桿倍數必須大於等於 1，收到: {leverage}")
    if hold_side not in ["long", "short"]:
        raise ValueError(f"持倉方向必須為 'long' 或 'short'，收到: {hold_side}")

    url = "https://api.bitget.com/api/mix/v1/account/setLeverage"
    timestamp = get_timestamp()
    method = "POST"
    request_path = "/api/mix/v1/account/setLeverage"
    body_dict = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "leverage": str(leverage),
        "holdSide": hold_side
    }
    body = json.dumps(body_dict)
    sign = bitget_sign(timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, headers=headers, data=body, timeout=5)
        result = resp.json()
        if result.get("code") != "00000":
            raise ValueError(f"設置槓桿失敗，API 回應: {result.get('msg', result)}")
        return result
    except Exception as e:
        raise RuntimeError(f"設置槓桿請求失敗: {str(e)}")

#查詢資產
def get_umcbl_usdt_balance():
    timestamp = str(int(time.time() * 1000))
    method = "GET"
    request_path = "/api/mix/v1/account/accounts"
    query = "?productType=umcbl"
    pre_hash = f"{timestamp}{method}{request_path}{query}"
    signature = hmac.new(BITGET_API_SECRET.encode('utf-8'), pre_hash.encode('utf-8'), digestmod=hashlib.sha256)
    signature = base64.b64encode(signature.digest()).decode()
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE
    }
    url = f"https://api.bitget.com{request_path}{query}"
    res = requests.get(url, headers=headers)
    data = res.json()
    if data.get("code") == "00000" and data.get("data"):
        for asset in data["data"]:
            if asset.get("marginCoin") == "USDT":
                equity = float(asset.get("equity", 0))
                available = float(asset.get("available", 0))
                margin = float(asset.get("margin", 0))
                return {
                    "equity": equity,
                    "available": available,
                    "margin": margin
                }
        return {"error": "查無 USDT 資產"}
    else:
        return {"error": data.get("msg", data)}

# 使用範例
result = get_umcbl_usdt_balance()
if "error" in result:
    print("查詢失敗：", result["error"])
else:
    print(f"U本位合約帳戶 USDT 資產：")
    print(f"帳戶總權益（equity）：{result['equity']:.4f} USDT")
    print(f"可用餘額（available）：{result['available']:.4f} USDT")
    print(f"已用保證金（margin）：{result['margin']:.4f} USDT")

#USDT 轉 size
def usdt_margin_to_size(usdt, price, leverage):
    """用保證金金額換算合約 size，考慮槓桿"""
    if not price or not usdt or not leverage:
        return None
    return round(float(usdt) * float(leverage) / float(price), 6)

#全部平倉API
def bitget_close_position(symbol, margin_coin, hold_side):
    url = "https://api.bitget.com/api/mix/v1/plan/closePositions"
    request_path = "/api/mix/v1/plan/closePositions"
    timestamp = get_timestamp()
    method = "POST"
    body_dict = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "holdSide": hold_side.lower()
    }
    body = json.dumps(body_dict)
    sign = bitget_sign(timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
    print("【DEBUG】[全部平倉]Request body:", body)
    print("【DEBUG】[全部平倉]Request url:", url)
    resp = requests.post(url, headers=headers, data=body)
    print("【DEBUG】[全部平倉]Response:", resp.text)
    return resp.json()

#部分平倉API
def bitget_partial_close_position(symbol, margin_coin, hold_side, size):
    url = "https://api.bitget.com/api/mix/v1/order/placeOrder"
    request_path = "/api/mix/v1/order/placeOrder"
    timestamp = get_timestamp()
    method = "POST"
    # side: close_long or close_short
    side = "close_long" if hold_side.lower() == "long" else "close_short"
    body_dict = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "side": side,
        "orderType": "market",
        "size": str(size)
    }
    body = json.dumps(body_dict)
    sign = bitget_sign(timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
    print("【DEBUG】[部分平倉]Request body:", body)
    print("【DEBUG】[部分平倉]Request url:", url)
    resp = requests.post(url, headers=headers, data=body)
    print("【DEBUG】[部分平倉]Response:", resp.text)
    return resp.json()

#TP/SL 掛單 API
def bitget_place_tpsl(symbol, margin_coin, tp_price, sl_price, hold_side):
    url = "https://api.bitget.com/api/mix/v1/plan/placeTPSL"
    timestamp = get_timestamp()
    method = "POST"
    request_path = "/api/mix/v1/plan/placeTPSL"
    body_dict = {
        "symbol": symbol,
        "marginCoin": margin_coin,
        "holdSide": hold_side,   # "long" or "short"
    }
    if tp_price:
        body_dict["triggerPrice"] = str(tp_price)
        body_dict["planType"] = "pos_profit"
    if sl_price:
        body_dict["triggerPrice"] = str(sl_price)
        body_dict["planType"] = "pos_loss"
    body = json.dumps(body_dict)
    sign = bitget_sign(timestamp, method, request_path, body)
    headers = {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, data=body)
    return resp.json()

#查詢當前槓桿值
def get_current_leverage(symbol, margin_coin="USDT"):
    try:
        # 確保 symbol 格式與 Bitget API 一致（例如 ETHUSDT_UMCBL）
        if not symbol.endswith("_UMCBL"):
            symbol = f"{symbol}_UMCBL"
        url = "https://api.bitget.com/api/mix/v1/account/account"
        timestamp = get_timestamp()
        method = "GET"
        request_path = "/api/mix/v1/account/account"
        query = f"?symbol={symbol}&marginCoin={margin_coin}"
        pre_hash = f"{timestamp}{method}{request_path}{query}"
        signature = hmac.new(BITGET_API_SECRET.encode('utf-8'), pre_hash.encode('utf-8'), digestmod=hashlib.sha256)
        signature = base64.b64encode(signature.digest()).decode()
        headers = {
            "ACCESS-KEY": BITGET_API_KEY,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": BITGET_PASSPHRASE
        }
        resp = requests.get(url + query, headers=headers, timeout=5)
        result = resp.json()
        print(f"【DEBUG】get_current_leverage API 回應: {json.dumps(result, ensure_ascii=False, indent=2)}")
        if result.get("code") == "00000" and result.get("data"):
            leverage = int(result["data"].get("leverage", 1))
            if leverage <= 1:  # 如果槓桿值為 1x，可能是未設置，改用預設值
                print(f"【DEBUG】API 返回槓桿值 {leverage}x 無效，使用預設值 30x")
                return 30
            return leverage
        else:
            print(f"【DEBUG】API 回應錯誤: {result.get('msg', '未知錯誤')}")
            return None
    except Exception as e:
        print(f"查詢當前槓桿失敗: {str(e)}")
        return None


# ========== symbol 正規化 ==========

def normalize_symbol(symbol):
    """將 symbol 統一轉為 Bitget API 標準格式 ETHUSDT_UMCBL"""
    s = symbol.upper().replace('-', '').replace('/', '')
    if s.endswith('_UMCBL'):
        return s
    if s.endswith('USDT'):
        return s + '_UMCBL'
    return s + 'USDT_UMCBL'

def match_symbol(api_symbol, user_symbol):
    """允許 ETHUSDT == ETHUSDT_UMCBL 的比對"""
    return api_symbol.replace('_UMCBL', '') == user_symbol.replace('_UMCBL', '')

# ========== Telegram UI ==========
def persistent_menu_keyboard():
    keyboard = [
        ["📊 查詢目前獲利"],
        ["📋 查詢詳細持倉"],
        ["💰 查詢資產"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# -------- 新增 /start 指令處理器 --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "歡迎使用 Bitget 機器人，請選擇功能：\n\n"
        "查價請輸入 /price 幣種 例如 /price BTC\n"
        "下單請直接輸入 AI 指令，如：BTCUSDT_UMCBL 多單 100USDT 市價 10x"
        "⚠️【重要提醒】⚠️\n"
        "1. Bitget 合約的全倉/逐倉模式需至官網或 App 手動切換，API 無法自動切換。\n"
        "2. 逐倉模式下，若止損價格超過強平價，系統會拒單，請留意風控提示。"
        ,
        reply_markup=persistent_menu_keyboard()
    )

# -------- 新增 /price 指令處理器 --------
async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        symbol = args[0].upper() if args else "BTC"
        # 自動補全成合約格式
        if not symbol.endswith("USDT_UMCBL"):
            symbol = symbol + "USDT_UMCBL"
        price = get_bitget_price(symbol)
        if price:
            await update.message.reply_text(f"{symbol} 現價：{price}", reply_markup=persistent_menu_keyboard())
        else:
            await update.message.reply_text(f"查詢失敗，請檢查幣種是否支援合約，如 BTC、ETH、SOL...", reply_markup=persistent_menu_keyboard())
    except Exception as e:
        await update.message.reply_text("查價指令格式錯誤，請輸入 /price BTC 或 /price ETH", reply_markup=persistent_menu_keyboard())

# -------- 功能選單 --------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # 判斷用戶輸入的文字
    if text == "📊 查詢目前獲利":
        data = get_all_positions()
        msg = ""
        total_pnl = 0
        total_realized = 0
        if data.get('code') == '00000' and data.get('data'):
            for pos in data['data']:
                symbol = pos.get('symbol', '')
                pnl = float(pos.get('unrealizedPL', '0'))
                realized = float(pos.get('achievedProfits', '0'))
                size = float(pos.get('total', '0'))
                entry = float(pos.get('averageOpenPrice', '0'))
                leverage = int(data.get("leverage") or 1)
                if size > 0 and entry > 0 and leverage > 0:
                    msg += f"{symbol} 未實現盈虧：{pnl:.8f}\n"
                    total_pnl += pnl
                    total_realized += realized
            if msg:
                msg += (
                    "---------------------\n"
                    f"總盈虧（未實現+已實現）：{(total_pnl + total_realized):.8f}\n"
                )
                await update.message.reply_text(msg, reply_markup=persistent_menu_keyboard())
            else:
                await update.message.reply_text("查無持倉", reply_markup=persistent_menu_keyboard())
        else:
            await update.message.reply_text(f"查詢失敗，API訊息：{data.get('msg', data)}", reply_markup=persistent_menu_keyboard())
    elif text == "📋 查詢詳細持倉":
        data = get_all_positions()
        msg = "📋 詳細持倉資訊\n"
        msg += "=====================\n\n"
        if data.get('code') == '00000' and data.get('data'):
            positions = data.get('data')
            if positions:
                for i, pos in enumerate(positions, 1):
                    symbol = pos.get('symbol', '未知交易對')
                    hold_side = pos.get('holdSide', '未知方向').capitalize()
                    total_size = float(pos.get('total', '0'))
                    entry_price = float(pos.get('averageOpenPrice', '0'))
                    unrealized_pl = float(pos.get('unrealizedPL', '0'))
                    achieved_profits = float(pos.get('achievedProfits', '0'))
                    leverage = int(pos.get('leverage', 1))
                    margin = float(pos.get('margin', '0'))
                    margin_mode = pos.get('marginMode', '未知模式').capitalize()
                    mark_price = float(pos.get('markPrice', '0')) if pos.get('markPrice') else None
                    
                    # 只顯示有持倉的項目
                    if total_size > 0:
                        msg += f"持倉 {i}: {symbol}\n"
                        msg += f"方向: {hold_side}\n"
                        msg += f"持倉數量: {total_size:.6f}\n"
                        msg += f"平均開倉價: {entry_price:.2f}\n"
                        # 優先顯示標記價格，若無則嘗試獲取最新價格
                        if mark_price and mark_price > 0:
                            msg += f"標記價格: {mark_price:.2f}\n"
                        else:
                            latest_price = get_bitget_price(symbol)
                            if latest_price:
                                msg += f"最新價格: {latest_price:.2f}\n"
                            else:
                                msg += f"最新價格: 無法獲取\n"
                        msg += f"未實現盈虧: {unrealized_pl:.8f}\n"
                        msg += f"已實現盈虧: {achieved_profits:.8f}\n"
                        msg += f"槓桿倍數: {leverage}x\n"
                        msg += f"保證金: {margin:.4f} USDT\n"
                        msg += f"保證金模式: {margin_mode}\n"
                        msg += "---------------------\n\n"
                if "持倉 1" not in msg:  # 如果沒有任何有效持倉
                    msg += "查無持倉\n"
            else:
                msg += "查無持倉\n"
            await update.message.reply_text(msg, reply_markup=persistent_menu_keyboard())
        else:
            await update.message.reply_text(f"查詢失敗，API訊息：{data.get('msg', data)}", reply_markup=persistent_menu_keyboard())
    elif text == "💰 查詢資產":
        data = get_umcbl_usdt_balance()
        if data and "error" not in data:
            equity = float(data.get("equity", 0))
            available = float(data.get("available", 0))
            margin = float(data.get("margin", 0))
            msg = (
                f"U本位合約總資產估值（USDT）\n"
                f"---------------------\n"
                f"帳戶總權益（equity）：{equity:.4f} USDT\n"
                f"可用餘額（available）：{available:.4f} USDT\n"
                f"已用保證金（margin）：{margin:.4f} USDT"
            )
        else:
            msg = f"查詢失敗，請稍後再試。{data.get('error') if isinstance(data, dict) else ''}"
        await update.message.reply_text(msg, reply_markup=persistent_menu_keyboard())
        return
    else:
        # 嘗試用自然語言下單
        await handle_order(update, context, text)


# ========== 智能下單 ==========

#多空方向轉換
def direction_to_side(direction):
    if str(direction).lower() in ["多單", "多", "long", "buy"]:
        return "open_long"
    return "open_short"

#市價限價轉換
def entry_type_to_order_type(entry_type):
    return "market" if "市" in entry_type or "market" in entry_type.lower() else "limit"

#解析json
def safe_json_parse(text):
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return json.loads(match.group(0))
    raise ValueError("找不到有效的 JSON 格式")

#AI PROMPT
BASE_PROMPT = """
你是一個合約交易智能助手，請將用戶的自然語言指令解析為 JSON。
請自動判斷是「開倉」還是「平倉」，並根據下方格式回傳 JSON，不要有其他說明。

格式如下：
{
  "action": "open" 或 "close",
  "symbol": "回傳幣種（用戶輸入的幣種名稱不要刪去簡化 例如FATCOIN、ETH、SOL、VIRTUAL ，幣種須加上USDT_UMCBL，如已有USDT則只加_UMCBL，例如：BTCUSDT_UMCBL；若無法確定交易對則填 'unknown'）",
  "direction": "long" 或 "short",
  "close_type": "usdt"（平倉才需填，開倉為 null）,
  "value": 要平倉的 USDT 金額（平倉填金額，開倉為 null）,
  "entry_type": "market" 或 "limit"（開倉用，平倉可 null）,
  "leverage": 槓桿數字（如 10，若無填 null）,
  "amount": 下單金額 USDT（開倉用，平倉為 null）,
  "price": 限價價格（限價開倉用，平倉為 null）,
  "take_profit": 止盈價（開倉用，平倉為 null）,
  "stop_loss": 止損價（開倉用，平倉為 null）,
  "marginMode": "cross" 或 "isolated"（若無填則預設為 'isolated'）
}

請依照下列規則：
- amount 與 value 都只允許 USDT 金額（不要回傳幣數）。
- 若用戶沒提到「逐倉」或「全倉」等字眼，請將 marginMode 預設為 'isolated'。
- 當用戶明確說明「全倉」時，marginMode 請填 'cross'；說明「逐倉」時，請填 'isolated'。
- 若無法確定交易對（symbol），請將 symbol 設為 'unknown'，不要預設為任何交易對。
- 請勿回傳多餘說明，只回傳 JSON 格式。

指令：
"""


#處理下單請求
async def handle_order(update, context, user_input):
    prompt = BASE_PROMPT + user_input
    reply_msg = "發生未知錯誤。"
    try:
        # AI 解析
        response = model.generate_content(prompt)
        reply = response.text.strip()
        try:
            data = safe_json_parse(reply)
        except Exception as e:
            raise ValueError(f"AI回傳格式錯誤，請重新描述指令\n原始回應：{reply}")

        action = data.get("action", "open")
        data["margin_coin"] = "USDT"

        # debug AI 解析結果
        print(f"【DEBUG】AI 解析結果: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # 檢查交易對是否為 unknown
        if data.get("symbol") == "unknown":
            reply_msg = "無法識別交易對，請明確指定交易對（例如：BTC、ETH、SOL 等）。"
            await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
            return

        # ----------- 平倉 -----------
        if action == "close":
            norm_symbol = normalize_symbol(data.get("symbol"))
            direction = data.get("direction", "long")
            value = safe_float(data.get("value"))  # value 是 USDT 金額
            positions = get_all_positions()
            print("【DEBUG】positions:", json.dumps(positions, ensure_ascii=False, indent=2))   

            pos = None
            total_size = 0
            for p in positions.get('data', []):
                if match_symbol(p['symbol'], norm_symbol) and p.get("holdSide") == direction:
                    total_size = safe_float(p.get("total"), 0)
                    if total_size > 0:
                        pos = p
                        break

            if not pos or total_size <= 0:
                reply_msg = f"查無 {norm_symbol} {direction} 持倉，或持倉量為 0。"
            else:
                # 全部平倉
                if value is None or value == 0:
                    res = bitget_close_position(norm_symbol, "USDT", direction)
                    reply_msg = f"{norm_symbol} {direction} 全部平倉結果：\n{json.dumps(res, ensure_ascii=False, indent=2)}"
                else:
                    price = get_bitget_price(norm_symbol)
                    leverage = safe_float(pos.get("leverage"), 1)
                    close_size = usdt_margin_to_size(value, price, leverage)
                    min_size = 0.001
                    if close_size < min_size:
                        raise ValueError(f"平倉數量({close_size}) 低於最小下單量({min_size})")
                    if close_size > total_size:
                        close_size = total_size  # 最多只能平全部
                    res = bitget_partial_close_position(norm_symbol, "USDT", direction, close_size)
                    reply_msg = (
                        f"{norm_symbol} {direction} 部分平倉（保證金 {value}U × 槓桿 {leverage} = 倉位約 {close_size:.6f}）結果：\n"
                        f"{json.dumps(res, ensure_ascii=False, indent=2)}"
                    )

        # ----------- 開倉 -----------
        elif action == "open":
            # 組裝下單參數
            symbol = normalize_symbol(data.get("symbol"))
            # 強制 direction/hold_side 格式
            direction_raw = str(data.get("direction", "long")).lower()
            if direction_raw in ["多單", "多", "long", "buy"]:
                side = "open_long"
                hold_side = "long"
            else:
                side = "open_short"
                hold_side = "short"
            order_type = data.get("entry_type", "market")
            margin_mode = data.get("marginMode", "isolated")
            # 檢查是否指定槓桿，若無則透過 API 查詢
            if data.get("leverage") is None or safe_int(data.get("leverage"), 0) <= 0:
                leverage = get_current_leverage(symbol)
                if leverage is None:
                    leverage = 30  # API 查詢失敗時的預設值，調整為 30x
                    reply_msg = f"無法查詢當前槓桿，使用預設值 {leverage}x。如需調整，請在指令中指定槓桿倍數（例如：eth 限2510 tp2600 sl2500 2u long 20x）。"
                    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
                else:
                    reply_msg = f"未指定槓桿，使用帳戶當前槓桿值 {leverage}x。如需調整，請在指令中指定槓桿倍數。"
                    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
            else:
                leverage = safe_int(data.get("leverage"), 1)
            amount = safe_float(data.get("amount"), 0)
            if amount <= 0:
                raise ValueError("下單金額必須大於 0")
            price = safe_float(data.get("price")) if data.get("price") else None
            take_profit = safe_float(data.get("take_profit")) if data.get("take_profit") else None
            stop_loss = safe_float(data.get("stop_loss")) if data.get("stop_loss") else None

            # 檢查當前槓桿，避免不必要設置
            current_leverage = get_current_leverage(symbol)
            if current_leverage is None or current_leverage != leverage:
                set_leverage_result = set_leverage(symbol, "USDT", leverage, hold_side)
                if set_leverage_result.get("code") != "00000":
                    error_msg = set_leverage_result.get("msg", "未知錯誤")
                    reply_msg = f"設置槓桿失敗：{error_msg}\n可能是保證金不足或已有持倉限制，請檢查帳戶餘額或降低槓桿倍數。\n⚠️ 提醒：Bitget 的逐倉/全倉模式需在官網或 App 手動切換。"
                    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
                    return
            else:
                print(f"槓桿已是 {leverage}x，無需重新設置")

            # 計算 size
            if order_type == "market":
                cur_price = get_bitget_price(symbol)
                if cur_price is None:
                    raise ValueError("無法獲取當前價格，請稍後再試")
                size = usdt_margin_to_size(amount, cur_price, leverage)
                entry_price = cur_price  # 用於強平價計算
            elif order_type == "limit":
                if not price:
                    raise ValueError("限價單必須指定 price")
                size = usdt_margin_to_size(amount, price, leverage)
                entry_price = price  # 用於強平價計算
            else:
                raise ValueError("未知的 order_type")

            # Bitget 最小下單量通常為 0.001
            if size < 0.001:
                reply_msg = f"下單失敗：下單金額太小，請增加金額或降低槓桿。"
                await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
                return

            # 逐倉模式下檢查止損價是否超過強平價
            if margin_mode == "isolated" and stop_loss is not None:
                liq_price = calc_liq_price_isolated(entry_price, leverage, hold_side)
                if hold_side == "long" and stop_loss < liq_price:
                    reply_msg = f"下單失敗：止損價 {stop_loss} 低於預估強平價 {liq_price:.2f}，在逐倉模式下不允許設置低於強平價的止損（多單）。請調整止損價或切換至全倉模式。"
                    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
                    return
                elif hold_side == "short" and stop_loss > liq_price:
                    reply_msg = f"下單失敗：止損價 {stop_loss} 高於預估強平價 {liq_price:.2f}，在逐倉模式下不允許設置高於強平價的止損（空單）。請調整止損價或切換至全倉模式。"
                    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())
                    return

            # 直接帶入 TP/SL
            order_dict = {
                "symbol": symbol,
                "marginCoin": "USDT",
                "side": side,
                "orderType": order_type,
                "size": str(size),
                "marginMode": margin_mode
            }
            if order_type == "limit" and price:
                order_dict["price"] = str(price)
            if take_profit:
                order_dict["presetTakeProfitPrice"] = str(take_profit)
            if stop_loss:
                order_dict["presetStopLossPrice"] = str(stop_loss)

            # 下單
            res = bitget_place_order(order_dict)
            if res.get("code") != "00000":
                error_msg = res.get("msg", "未知錯誤")
                reply_msg = f"{symbol} {side} 下單失敗：{error_msg}\n⚠️ 提醒：Bitget 的逐倉/全倉模式需在官網或 App 手動切換，止損價可能超過強平價限制。"
            else:
                msg = f"{symbol} {side} 下單結果：\n{json.dumps(res, ensure_ascii=False, indent=2)}"
                # 逐倉模式下附加強平價提示
                if margin_mode == "isolated":
                    liq_price = calc_liq_price_isolated(entry_price, leverage, hold_side)
                    msg += f"\n⚠️ 逐倉模式預估強平價：{liq_price:.2f}，止損價不得{ '低於' if hold_side == 'long' else '高於' }此價格。"
                reply_msg = msg

        else:
            reply_msg = "無法判斷是開倉、平倉還是 TP/SL 修改指令，請確認語句。"

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        reply_msg = f"解析或下單/平倉失敗: {str(e)}\n\n如需協助請聯絡管理員。"
    await update.message.reply_text(reply_msg, reply_markup=persistent_menu_keyboard())


    

# ========== 逐倉強平價格計算 ==========
def calc_liq_price_isolated(entry_price, leverage, direction, mmr=0.005, taker_fee=0.0006):
    """
    計算Bitget USDT本位逐倉強平價（簡化版）
    entry_price: 開倉價
    leverage: 槓桿
    direction: "long" or "short"
    mmr: 維持保證金率，預設0.5%
    taker_fee: 吃單手續費率，預設0.06%
    """
    total_rate = mmr + taker_fee
    if direction == "long":
        liq_price = entry_price * (1 - 1 / leverage + total_rate)
    elif direction == "short":
        liq_price = entry_price * (1 + 1 / leverage - total_rate)
    else:
        raise ValueError("direction 必須為 long 或 short")
    return liq_price

# ========== 防呆機制 ==========
def safe_float(val, default=None):
    """安全轉 float，遇到 None、空字串、'null'、'None' 都給 default"""
    try:
        if val is None or str(val).strip().lower() in ['', 'null', 'none']:
            return default
        return float(val)
    except Exception:
        return default

def safe_int(val, default=None):
    """安全轉 int"""
    try:
        if val is None or str(val).strip().lower() in ['', 'null', 'none']:
            return default
        return int(val)
    except Exception:
        return default

# ========== 主程式 ==========
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), menu_handler))
    print("Bot is running...")
    app.run_polling()