import os
import sys
import json
import time
import pandas as pd
from datetime import datetime

sys.path.insert(0, './src')  # Adjust if necessary

from simple_exchange import SimpleExchangeManager
from cipherb import detect_exact_cipherb_signals
import requests

# Load coins list from file
def load_coins():
    with open('coins.txt') as f:
        return [line.strip().upper() for line in f if line.strip() and not line.startswith('#')]

# Send alerts to Telegram
def send_telegram_alert(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    print(f"Telegram response: {response.status_code}")
    response.raise_for_status()

def main():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')    

    coins = load_coins()
    exchange = SimpleExchangeManager()

    alerts = []
    analyzed_count = 0

    for symbol in coins:
        try:
            data, _ = exchange.fetch_ohlcv_with_fallback(symbol, '15m', 100)
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

            signals_df = detect_exact_cipherb_signals(df)
            if signals_df.empty:
                continue

            latest_signal = signals_df.iloc[-1]
            candle_time = df.index[-1]

            current_time = datetime.utcnow()
            if (current_time - candle_time).total_seconds() > 30 * 60:  # freshness 30 mins
                continue

            wt1 = latest_signal['wt1']
            wt2 = latest_signal['wt2']
            message = None
            if latest_signal['buySignal'] and wt1 <= -60 and wt2 <= -60:
                message = f"📈 BUY signal for {symbol} at {candle_time.strftime('%Y-%m-%d %H:%M')} UTC"
            elif latest_signal['sellSignal'] and wt1 >= 60 and wt2 >= 60:
                message = f"📉 SELL signal for {symbol} at {candle_time.strftime('%Y-%m-%d %H:%M')} UTC"

            if message:
                alerts.append(message)

            analyzed_count += 1
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    print(f"Analyzed {analyzed_count} coins. Found {len(alerts)} alerts.")

    if alerts:
        full_message = "\n".join(alerts)
        send_telegram_alert(bot_token, chat_id, full_message)

if __name__ == "__main__":
    main()
