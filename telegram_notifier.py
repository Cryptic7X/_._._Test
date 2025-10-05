"""
Telegram notification module for Gaussian Channel alerts
"""

import os
import requests
from datetime import datetime


class TelegramNotifier:
    """Send Telegram notifications for trading alerts"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def is_configured(self):
        """Check if Telegram credentials are configured"""
        return bool(self.bot_token and self.chat_id)
    
    def send_message(self, message, parse_mode='HTML'):
        """
        Send message to Telegram
        
        Args:
            message: Text message to send
            parse_mode: 'HTML' or 'Markdown'
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_configured():
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Telegram send failed: {str(e)}")
            return False
    
    def format_alert(self, result):
        """
        Format trading alert for Telegram
        
        Args:
            result: Analysis result dict
        
        Returns:
            str: Formatted HTML message
        """
        arrow = '↑' if result['direction'] == 'from_below' else '↓'
        emoji = '🔴' if result['band'] == 'hband' else '🔵'
        
        # Determine signal emoji
        signal_emoji = '🟢' if result['signal'] == 'BULLISH' else '🔴'
        
        # Format time in IST
        utc_time = result['timestamp']
        ist_time = utc_time + pd.Timedelta(hours=5, minutes=30)
        
        # Create TradingView chart link
        base_coin = result['coin'].replace('USDT', '')
        chart_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{base_coin}USDT&interval=15"
        
        message = (
            f"{emoji} <b>{result['coin']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Signal:</b> {result['band'].upper()}{arrow} {signal_emoji} {result['signal']}\n"
            f"<b>Time:</b> {ist_time.strftime('%Y-%m-%d %H:%M IST')}\n"
            f"<b>Close:</b> ${result['close']:.4f}\n"
            f"<b>Band:</b> ${result['band_value']:.4f}\n"
            f"<b>Filter:</b> ${result['filter']:.4f}\n"
            f"<b>Exchange:</b> {result['exchange'].upper()}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<a href='{chart_link}'>📊 View Chart</a>"
        )
        
        return message
    
    def send_alert(self, result):
        """
        Send formatted trading alert to Telegram
        
        Args:
            result: Analysis result dict
        
        Returns:
            bool: True if successful
        """
        message = self.format_alert(result)
        return self.send_message(message)
    
    def send_summary(self, alerts, total_coins, failed_count):
        """
        Send analysis summary to Telegram
        
        Args:
            alerts: List of alert dicts
            total_coins: Total number of coins analyzed
            failed_count: Number of failed analyses
        
        Returns:
            bool: True if successful
        """
        if not alerts:
            message = (
                f"📊 <b>Gaussian Channel 15m Analysis</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>Coins Analyzed:</b> {total_coins}\n"
                f"<b>Signals Detected:</b> 0\n"
                f"<b>Status:</b> No alerts ✅"
            )
        else:
            hband_up = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_below'])
            hband_down = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_above'])
            lband_up = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_below'])
            lband_down = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_above'])
            
            message = (
                f"📊 <b>Gaussian Channel 15m Analysis</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>Coins Analyzed:</b> {total_coins}\n"
                f"<b>Signals Detected:</b> {len(alerts)}\n"
                f"<b>Failed:</b> {failed_count}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>Breakdown:</b>\n"
                f"  🔴 HBand ↑: {hband_up}\n"
                f"  🔴 HBand ↓: {hband_down}\n"
                f"  🔵 LBand ↓: {lband_down}\n"
                f"  🔵 LBand ↑: {lband_up}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>"
            )
        
        return self.send_message(message)


# Fix import
import pandas as pd
