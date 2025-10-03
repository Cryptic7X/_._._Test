import time
import json
import pandas as pd
from simple_exchange import SimpleExchangeManager
from cipherb import detect_exact_cipherb_signals
from deduplication_cache import SimpleCache
import requests

TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'

def send_telegram_alerts(signals):
    if not signals:
        print("No signals to send.")
        return
    bot_token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    message = "📊 CipherB Alerts\n"
    for i, s in enumerate(signals, 1):
        message += f"{i}. {s['symbol']} | {s['signal_type']} | Price: ${s['price']:.4f}\n"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Alerts sent successfully")
    else:
        print("Failed to send alerts:", response.text)

def run_analysis():
    exchange = SimpleExchangeManager()
    cache = SimpleCache()
    with open('coins.txt', 'r') as f:
        coins = [line.strip() for line in f if line.strip()]
    signals = []
    start_time = time.time()
    for symbol in coins:
        data, _ = exchange.fetch_ohlcv_with_fallback(symbol, '30m', 200)
        if not data or len(data.get('timestamp', [])) < 50:
            continue
        df = pd.DataFrame({
            'high': data['high'],
            'low': data['low'],
            'close': data['close'],
            'timestamp': data['timestamp']
        })
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        signal_df = detect_exact_cipherb_signals(df)
        if signal_df.empty:
            continue
        latest = signal_df.iloc[-1]
        wt1 = float(latest['wt1'])
        wt2 = float(latest['wt2'])
        if latest['buySignal'] and (wt1 <= -60 and wt2 <= -60):
            signal_type = 'BUY'
        elif latest['sellSignal'] and (wt1 >= 60 and wt2 >= 60):
            signal_type = 'SELL'
        else:
            continue
        if cache.should_send(symbol, signal_type):
            signals.append({
                'symbol': symbol,
                'signal_type': signal_type,
                'price': data['close'][-1]
            })
        elapsed = time.time() - start_time
        if elapsed > 900:  # 15 minutes total
            print("Stopping early to keep within 15 minutes runtime")
            break
    print(f"Found {len(signals)} signals")
    send_telegram_alerts(signals)

if __name__ == "__main__":
    run_analysis()
