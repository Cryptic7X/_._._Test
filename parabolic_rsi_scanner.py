import os
import ccxt
import pandas as pd
from datetime import datetime
from indicators import calculate_parabolic_rsi, detect_strong_signals
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
FRESHNESS_MINUTES = 60  # Only alert on signals within last 60 minutes (1 hour)

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

def scan_coins(symbols, timeframe):
    """Scan all coins for Parabolic RSI strong signals"""
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
            
            # Detect strong signals only (Big Diamonds) with freshness check
            signals = detect_strong_signals(
                df, 
                upper_threshold=UPPER_THRESHOLD,
                lower_threshold=LOWER_THRESHOLD,
                timeframe=timeframe,
                freshness_minutes=FRESHNESS_MINUTES  # Add freshness parameter
            )
            
            if signals:
                latest = df.iloc[-1]
                tv_link, cg_link = create_chart_links(symbol, timeframe)
                
                # Calculate signal age for display
                signal_age_minutes = (datetime.utcnow() - latest['timestamp'].to_pydatetime().replace(tzinfo=None)).total_seconds() / 60
                
                alerts.append({
                    'symbol': symbol,
                    'signals': signals,
                    'rsi': latest['rsi'],
                    'sar': latest['sar'],
                    'price': latest['close'],
                    'timestamp': latest['timestamp'],
                    'signal_age_minutes': signal_age_minutes,
                    'tv_link': tv_link,
                    'cg_link': cg_link
                })
                print(f"  ✓ Signal detected: {signals} (Age: {signal_age_minutes:.1f} min)")
            else:
                print(f"  - No fresh signals")
                
        except Exception as e:
            print(f"  ✗ Error processing {symbol}: {str(e)}")
            continue
    
    return alerts

def format_alert_message(alerts):
    """Format alerts for Telegram"""
    if not alerts:
        return None
    
    message = f"🔔 <b>Parabolic RSI Strong Signals</b>\n"
    message += f"📊 Timeframe: <b>{TIMEFRAME}</b>\n"
    message += f"⏰ Time: <b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}</b>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for alert in alerts:
        signal_emoji = "🔴" if 'STRONG_SELL' in alert['signals'] else "🟢"
        signal_text = "STRONG SELL" if 'STRONG_SELL' in alert['signals'] else "STRONG BUY"
        
        # Format signal age
        age_min = alert['signal_age_minutes']
        if age_min < 60:
            age_text = f"{age_min:.0f}m ago"
        else:
            age_text = f"{age_min/60:.1f}h ago"
        
        message += f"{signal_emoji} <b>{alert['symbol']}</b>\n"
        message += f"Signal: <b>{signal_text}</b> ({age_text})\n"
        message += f"RSI: <code>{alert['rsi']:.2f}</code>\n"
        message += f"SAR: <code>{alert['sar']:.2f}</code>\n"
        message += f"Price: <code>${alert['price']:.6f}</code>\n"
        message += f"📈 <a href=\"{alert['tv_link']}\">TradingView Chart</a>\n"
        message += f"🔥 <a href=\"{alert['cg_link']}\">CoinGlass Liquidations</a>\n"
        message += f"\n"
    
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Total Signals: <b>{len(alerts)}</b>"
    
    return message

def main():
    """Main scanner function"""
    print("=" * 60)
    print("Parabolic RSI Scanner - Strong Signals Only")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Freshness Window: {FRESHNESS_MINUTES} minutes")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 60)
    
    # Load coins from file
    symbols = load_coins('coins.txt')
    
    if not symbols:
        print("No coins to scan!")
        return
    
    # Scan all coins
    alerts = scan_coins(symbols, TIMEFRAME)
    
    # Send Telegram alert if signals found
    if alerts:
        print(f"\n✓ Found {len(alerts)} fresh signal(s)!")
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
    
    print("\n" + "=" * 60)
    print("Scan completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
