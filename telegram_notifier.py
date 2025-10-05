"""
Telegram notification module for Gaussian Channel alerts
"""

import os
import requests
from datetime import datetime
import pandas as pd


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
    
    def format_single_alert(self, result):
        """Format single alert in compact form"""
        arrow = '↑' if result['direction'] == 'from_below' else '↓'
        emoji = '🔴' if result['band'] == 'hband' else '🔵'
        signal_emoji = '🟢' if result['signal'] == 'BULLISH' else '🔴'
        
        # Format time in IST
        utc_time = result['timestamp']
        ist_time = utc_time + pd.Timedelta(hours=5, minutes=30)
        
        # Create TradingView chart link
        base_coin = result['coin'].replace('USDT', '')
        chart_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{base_coin}USDT&interval=15"
        
        return (
            f"{emoji} <b>{result['coin']}</b> | {result['band'].upper()}{arrow} {signal_emoji}\n"
            f"  💰 ${result['close']:.4f} | ⏰ {ist_time.strftime('%H:%M IST')}\n"
            f"  📊 <a href='{chart_link}'>Chart</a> | 🏦 {result['exchange'].upper()}"
        )
    
    def send_consolidated_alerts(self, alerts, total_coins, failed_count):
        """
        Send all alerts in ONE consolidated message
        
        Args:
            alerts: List of alert dicts
            total_coins: Total number of coins analyzed
            failed_count: Number of failed analyses
        
        Returns:
            bool: True if successful
        """
        if not alerts:
            # No signals detected
            message = (
                f"📊 <b>Gaussian Channel 15m Analysis</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔍 Analyzed: {total_coins} coins\n"
                f"🔔 Signals: 0\n"
                f"✅ Status: No alerts\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M IST')}"
            )
            return self.send_message(message)
        
        # Calculate breakdown
        hband_up = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_below'])
        hband_down = len([a for a in alerts if a['band'] == 'hband' and a['direction'] == 'from_above'])
        lband_up = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_below'])
        lband_down = len([a for a in alerts if a['band'] == 'lband' and a['direction'] == 'from_above'])
        
        # Build consolidated message
        message = (
            f"📊 <b>Gaussian Channel 15m Analysis</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Analyzed: {total_coins} coins\n"
            f"🔔 Signals: {len(alerts)}\n"
            f"❌ Failed: {failed_count}\n\n"
        )
        
        # Add breakdown
        message += f"<b>📈 Breakdown:</b>\n"
        if hband_up > 0:
            message += f"  🔴 HBand ↑: {hband_up}\n"
        if hband_down > 0:
            message += f"  🔴 HBand ↓: {hband_down}\n"
        if lband_down > 0:
            message += f"  🔵 LBand ↓: {lband_down}\n"
        if lband_up > 0:
            message += f"  🔵 LBand ↑: {lband_up}\n"
        
        message += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"<b>🚨 ALERTS:</b>\n\n"
        
        # Add all alerts
        for i, alert in enumerate(alerts, 1):
            message += f"{i}. {self.format_single_alert(alert)}\n\n"
        
        # Add footer
        current_time = datetime.now()
        ist_time = current_time + pd.Timedelta(hours=5, minutes=30)
        message += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"⏰ {ist_time.strftime('%Y-%m-%d %H:%M IST')}"
        
        # Split message if too long (Telegram limit: 4096 characters)
        if len(message) > 4000:
            # Send in chunks
            return self._send_long_message(message)
        
        return self.send_message(message)
    
    def _send_long_message(self, message):
        """Split and send long messages"""
        max_length = 4000
        parts = []
        
        # Split by alerts
        lines = message.split('\n\n')
        current_part = ""
        
        for line in lines:
            if len(current_part) + len(line) + 2 < max_length:
                current_part += line + "\n\n"
            else:
                if current_part:
                    parts.append(current_part)
                current_part = line + "\n\n"
        
        if current_part:
            parts.append(current_part)
        
        # Send all parts
        success = True
        for i, part in enumerate(parts):
            if i == 0:
                sent = self.send_message(part)
            else:
                # Add continuation header
                cont_msg = f"<b>📊 Continued... (Part {i+1})</b>\n\n{part}"
                sent = self.send_message(cont_msg)
            
            if not sent:
                success = False
        
        return success
