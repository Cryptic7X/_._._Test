import os
import ccxt
import pandas as pd
import json
from datetime import datetime, timedelta
from indicators import calculate_parabolic_rsi, detect_all_signals, should_alert
from data_fetcher import fetch_ohlcv_multi_exchange
from telegram_alerts import send_telegram_message

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TIMEFRAME = '30m'
RSI_LENGTH = 14
SAR_START = 0.02
SAR_INCREMENT = 0.02
SAR_MAX = 0.2
UPPER_THRESHOLD = 70
LOWER_THRESHOLD = 30
FRESHNESS_HOURS = 1  # Only alert signals within 1 hour

# Alert history file to prevent duplicates
ALERT_HISTORY_FILE = 'alert_history.json'

def load_coins(filename='coins.txt'):
    """Load coin symbols from text file"""
    try:
        with open(filename, 'r') as f:
            coins = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"Loaded {len(coins)} coins from {filename}")
        return coins
    except FileNotFoundError:
        print(f"Error: {filename} not found!")
        return []

def load_alert_history():
    """Load alert history to prevent duplicate alerts"""
    try:
        with open(ALERT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_alert_history(alert_history):
    """Save alert history to file"""
    try:
        with open(ALERT_HISTORY_FILE, 'w') as f:
            json.dump(alert_history, f, indent=2)
    except Exception as e:
        print(f"Error saving alert history: {e}")

def create_chart_links(symbol, timeframe='30m'):
    """Create TradingView and CoinGlass links"""
    # Convert timeframe to minutes
    timeframe_map = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440, '1w': 10080
    }
    timeframe_minutes = timeframe_map.get(timeframe, 30)
    
    # Clean symbol (remove /USDT or /USD)
    clean_symbol = symbol.replace('/USDT', '').replace('/USD', '').replace('/', '')
    
    # Create links
    tv_link = f"https://www.tradingview.com/chart/?symbol={clean_symbol}USDT&interval={timeframe_minutes}"
    cg_link = f"https://www.coinglass.com/pro/futures/LiquidationHeatMapNew?coin={clean_symbol}"
    
    return tv_link, cg_link

def scan_coins(symbols, timeframe, current_time, alert_history):
    """Scan all coins for ALL Parabolic RSI signals (regular + strong)"""
    alerts = []
    
    for symbol in symbols:
        try:
            print(f"Analyzing {symbol}...")
            
            # Fetch OHLCV data from multiple exchanges
            df = fetch_ohlcv_multi_exchange(symbol, timeframe, limit=100)
            
            if df is None or len(df) < 50:
                print(f"  ⚠ Insufficient data for {symbol}")
                continue
            
            # Calculate Parabolic RSI indicator
            df = calculate_parabolic_rsi(
                df, 
                rsi_length=RSI_LENGTH,
                sar_start=SAR_START,
                sar_increment=SAR_INCREMENT,
                sar_max=SAR_MAX
            )
            
            # Detect ALL signals (regular + strong + chart)
            all_signals = detect_all_signals(
                df, 
                upper_threshold=UPPER_THRESHOLD,
                lower_threshold=LOWER_THRESHOLD
            )
            
            if all_signals:
                latest = df.iloc[-1]
                candle_timestamp = latest['timestamp']
                
                # Check if we should alert (freshness + no duplicates)
                should_send_alert, fresh_signals = should_alert(
                    symbol, all_signals, candle_timestamp, alert_history, current_time
                )
                
                if should_send_alert:
                    tv_link, cg_link = create_chart_links(symbol, timeframe)
                    
                    alerts.append({
                        'symbol': symbol,
                        'signals': fresh_signals,
                        'rsi': latest['rsi'],
                        'sar': latest['sar'],
                        'price': latest['close'],
                        'timestamp': candle_timestamp,
                        'tv_link': tv_link,
                        'cg_link': cg_link
                    })
                    print(f"  ✓ Fresh signals: {fresh_signals}")
                else:
                    print(f"  - Signals detected but not fresh or duplicate: {all_signals}")
            else:
                print(f"  - No signals")
                
        except Exception as e:
            print(f"  ✗ Error processing {symbol}: {str(e)}")
            continue
    
    return alerts

def format_signal_text(signals):
    """Format signals for display"""
    signal_map = {
        'STRONG_BUY': '🟢 STRONG BUY',
        'STRONG_SELL': '🔴 STRONG SELL', 
        'REGULAR_BUY': '🟡 REGULAR BUY',
        'REGULAR_SELL': '🟠 REGULAR SELL',
        'CHART_STRONG_BUY': '💎 Chart Strong Buy',
        'CHART_STRONG_SELL': '💎 Chart Strong Sell',
        'CHART_REGULAR_BUY': '◇ Chart Regular Buy', 
        'CHART_REGULAR_SELL': '◇ Chart Regular Sell'
    }
    
    # Group signals by type
    strong_signals = [s for s in signals if 'STRONG' in s and 'CHART' not in s]
    regular_signals = [s for s in signals if 'REGULAR' in s and 'CHART' not in s]
    chart_signals = [s for s in signals if 'CHART' in s]
    
    # Format display
    display_signals = []
    
    # Show strong signals first (highest priority)
    if strong_signals:
        display_signals.extend([signal_map[s] for s in strong_signals])
    elif regular_signals:  # Only show regular if no strong signals
        display_signals.extend([signal_map[s] for s in regular_signals])
    
    # Add chart signals as additional info
    if chart_signals:
        display_signals.extend([signal_map[s] for s in chart_signals])
    
    return display_signals

def format_alert_message(alerts):
    """Format alerts for Telegram"""
    if not alerts:
        return None
    
    message = f"🔔 <b>Parabolic RSI Signals</b>\n"
    message += f"📊 Timeframe: <b>{TIMEFRAME}</b>\n"
    message += f"⏰ Time: <b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}</b>\n"
    message += f"🕐 Freshness: <b>Within {FRESHNESS_HOURS}h</b>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for alert in alerts:
        # Get primary signal for emoji
        signals = alert['signals']
        formatted_signals = format_signal_text(signals)
        
        # Use strongest signal for main emoji
        main_emoji = "🔴" if any('STRONG_SELL' in s for s in signals) else \
                     "🟢" if any('STRONG_BUY' in s for s in signals) else \
                     "🟠" if any('REGULAR_SELL' in s for s in signals) else "🟡"
        
        message += f"{main_emoji} <b>{alert['symbol']}</b>\n"
        
        # Show all signals
        for sig_text in formatted_signals:
            message += f"• {sig_text}\n"
        
        message += f"RSI: <code>{alert['rsi']:.2f}</code>\n"
        message += f"SAR: <code>{alert['sar']:.2f}</code>\n"
        message += f"Price: <code>${alert['price']:.6f}</code>\n"
        message += f"📈 <a href=\"{alert['tv_link']}\">TradingView Chart</a>\n"
        message += f"🔥 <a href=\"{alert['cg_link']}\">CoinGlass Liquidations</a>\n"
        message += f"\n"
    
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Total Alerts: <b>{len(alerts)}</b>"
    
    return message

def main():
    """Main scanner function"""
    current_time = datetime.now()
    
    print("=" * 70)
    print("Parabolic RSI Scanner - All Signals (Regular + Strong)")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Freshness Window: {FRESHNESS_HOURS} hour(s)")
    print(f"Started at: {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 70)
    
    # Load alert history
    alert_history = load_alert_history()
    print(f"Loaded {len(alert_history)} previous alert records")
    
    # Load coins from file
    symbols = load_coins('coins.txt')
    
    if not symbols:
        print("No coins to scan!")
        return
    
    # Scan all coins
    alerts = scan_coins(symbols, TIMEFRAME, current_time, alert_history)
    
    # Save updated alert history
    save_alert_history(alert_history)
    
    # Send Telegram alert if signals found
    if alerts:
        print(f"\n✓ Found {len(alerts)} fresh alert(s)!")
        message = format_alert_message(alerts)
        
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
            if success:
                print("✓ Telegram alert sent successfully!")
            else:
                print("✗ Failed to send Telegram alert")
        else:
            print("⚠ Telegram credentials not configured")
            print("\nMessage preview:")
            print(message)
    else:
        print("\n- No fresh signals detected")
    
    print("\n" + "=" * 70)
    print("Scan completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
