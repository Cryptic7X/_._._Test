"""
Run Gaussian Channel 15-Minute Analysis on Multiple Coins
Sends alerts to Telegram
"""

import os
from datetime import datetime
from gaussian_channel_15m_analyzer import GaussianChannel15mAnalyzer
from telegram_notifier import TelegramNotifier


def load_coins(filename='coins.txt'):
    """Load coin list from file"""
    if not os.path.exists(filename):
        print(f"❌ Error: {filename} not found")
        return []
    
    with open(filename, 'r') as f:
        coins = [line.strip() for line in f if line.strip()]
    
    return coins


def format_console_alert(result):
    """Format alert message for console"""
    arrow = '↑' if result['direction'] == 'from_below' else '↓'
    band_emoji = '🔴' if result['band'] == 'hband' else '🔵'
    
    return (
        f"{band_emoji} {result['coin']} | {result['band'].upper()}{arrow} | {result['signal']}\n"
        f"   Time: {result['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"   Close: ${result['close']:.4f} | Band: ${result['band_value']:.4f}\n"
        f"   Exchange: {result['exchange'].upper()}"
    )


def main():
    """Main execution function"""
    print("="*80)
    print("GAUSSIAN CHANNEL 15-MINUTE ANALYSIS")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80 + "\n")
    
    # Initialize Telegram notifier
    telegram = TelegramNotifier()
    telegram_enabled = telegram.is_configured()
    
    if telegram_enabled:
        print("✅ Telegram notifications enabled")
    else:
        print("⚠️  Telegram notifications disabled (credentials not found)")
    print()
    
    # Load coins
    coins = load_coins('coins.txt')
    
    if not coins:
        print("❌ No coins to analyze")
        return
    
    print(f"📋 Loaded {len(coins)} coins from coins.txt\n")
    
    # Initialize analyzer
    analyzer = GaussianChannel15mAnalyzer()
    
    # Track results
    alerts = []
    failed_coins = []
    
    # Analyze each coin
    print("🔍 Analyzing coins...\n")
    
    for i, coin in enumerate(coins, 1):
        print(f"[{i}/{len(coins)}] Analyzing {coin}...", end=' ')
        
        try:
            result = analyzer.analyze_coin(coin)
            
            if result:
                alerts.append(result)
                print("✅ SIGNAL DETECTED")
                print(format_console_alert(result))
                print()
                
                # Send Telegram alert immediately
                if telegram_enabled:
                    success = telegram.send_alert(result)
                    if success:
                        print("   ✓ Telegram alert sent")
                    else:
                        print("   ✗ Telegram alert failed")
                    print()
            else:
                print("⚪ No signal")
                
        except Exception as e:
            failed_coins.append(coin)
            print(f"❌ Failed: {str(e)}")
    
    # Print summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    print(f"Total Coins Analyzed: {len(coins)}")
    print(f"Signals Detected: {len(alerts)}")
    print(f"Failed: {len(failed_coins)}")
    
    if alerts:
        print(f"\n📊 Signal Breakdown:")
        hband_up = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_below'])
        hband_down = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_above'])
        lband_up = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_below'])
        lband_down = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_above'])
        
        print(f"   HBand ↑ (Bullish): {hband_up}")
        print(f"   HBand ↓ (Bearish): {hband_down}")
        print(f"   LBand ↓ (Bearish): {lband_down}")
        print(f"   LBand ↑ (Bullish): {lband_up}")
        
        print(f"\n🔔 ALERTS:")
        for alert in alerts:
            print(format_console_alert(alert))
            print()
    
    if failed_coins:
        print(f"\n⚠️  Failed Coins: {', '.join(failed_coins)}")
    
    # Send summary to Telegram
    if telegram_enabled:
        print("\n📤 Sending summary to Telegram...")
        success = telegram.send_summary(alerts, len(coins), len(failed_coins))
        if success:
            print("   ✓ Summary sent successfully")
        else:
            print("   ✗ Summary failed to send")
    
    print("\n" + "="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)


if __name__ == "__main__":
    main()
