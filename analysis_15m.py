#!/usr/bin/env python3
"""
CipherB 15m Analysis - Standalone Test
No AWS, no config files - just pure signal detection
"""

import os
import sys
import json
import time
import pandas as pd
from datetime import datetime
import requests

from simple_exchange import SimpleExchangeManager
from cipherb import detect_exact_cipherb_signals

def load_coins():
    """Load coins from coins.txt"""
    try:
        with open('coins.txt') as f:
            coins = [line.strip().upper() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Loaded {len(coins)} coins")
        return coins
    except:
        print("❌ Error loading coins.txt")
        return []

def send_telegram_alert(bot_token, chat_id, message):
    """Send alert to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Telegram sent successfully")
        return True
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def main():
    print("🔍 CipherB 15m Analysis - Test Run")
    print("=" * 50)
    
    # Load environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return
    
    # Load coins
    coins = load_coins()
    if not coins:
        return
    
    # Initialize exchange manager
    exchange = SimpleExchangeManager()
    
    analyzed_count = 0
    signal_count = 0
    alerts = []
    
    current_utc = datetime.utcnow()
    print(f"🕐 Analysis time: {current_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Analyze each coin
    for symbol in coins:
        try:
            # Fetch 15m OHLCV data
            data, exchange_used = exchange.fetch_ohlcv_with_fallback(symbol, '15m', 100)
            
            if not data or len(data.get('timestamp', [])) < 50:
                continue
            
            analyzed_count += 1
            
            # Create DataFrame
            df = pd.DataFrame({
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'timestamp': data['timestamp']
            })
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            # Calculate CipherB signals
            signals_df = detect_exact_cipherb_signals(df)
            
            if signals_df.empty:
                continue
            
            # Check LAST CLOSED candle only
            latest_signal = signals_df.iloc[-1]
            candle_time_utc = df.index[-1].to_pydatetime()
            
            # Freshness check: Signal must be < 30 minutes old
            time_diff = current_utc - candle_time_utc
            if time_diff.total_seconds() > (30 * 60):
                continue
            
            wt1 = float(latest_signal['wt1'])
            wt2 = float(latest_signal['wt2'])
            price = data['close'][-1]
            
            # Check BUY signal
            if latest_signal['buySignal'] and wt1 <= -60 and wt2 <= -60:
                signal_count += 1
                alert_msg = f"🟢 BUY: {symbol}\n"
                alert_msg += f"💰 Price: ${price:.4f}\n"
                alert_msg += f"📊 WT1: {wt1:.1f}, WT2: {wt2:.1f}\n"
                alert_msg += f"🕐 {candle_time_utc.strftime('%H:%M UTC')}\n"
                alerts.append(alert_msg)
                print(f"✅ {symbol} BUY: WT1={wt1:.1f}, WT2={wt2:.1f}")
            
            # Check SELL signal
            elif latest_signal['sellSignal'] and wt1 >= 60 and wt2 >= 60:
                signal_count += 1
                alert_msg = f"🔴 SELL: {symbol}\n"
                alert_msg += f"💰 Price: ${price:.4f}\n"
                alert_msg += f"📊 WT1: {wt1:.1f}, WT2: {wt2:.1f}\n"
                alert_msg += f"🕐 {candle_time_utc.strftime('%H:%M UTC')}\n"
                alerts.append(alert_msg)
                print(f"✅ {symbol} SELL: WT1={wt1:.1f}, WT2={wt2:.1f}")
                
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            continue
    
    # Send consolidated alert
    print("=" * 50)
    print(f"📊 SUMMARY:")
    print(f"  • Total coins: {len(coins)}")
    print(f"  • Analyzed: {analyzed_count}")
    print(f"  • Signals found: {signal_count}")
    
    if alerts:
        header = f"🌊 CipherB 15m Signals ({signal_count} total)\n"
        header += f"🕐 {current_utc.strftime('%H:%M:%S')} UTC\n\n"
        full_message = header + "\n".join(alerts)
        
        send_telegram_alert(bot_token, chat_id, full_message)
    else:
        print("⚪ No signals found")

if __name__ == "__main__":
    main()
