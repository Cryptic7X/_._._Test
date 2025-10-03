#!/usr/bin/env python3
"""
Telegram Bot for Gaussian Channel Alerts with Batched Messages
"""

import os
import requests
from typing import Optional, List
from datetime import datetime, timedelta

class TelegramBot:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram bot
        
        Args:
            bot_token: Telegram bot token (defaults to env var)
            chat_id: Telegram chat ID (defaults to env var)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send message to Telegram
        
        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or Markdown)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Telegram send error: {e}")
            return False
    
    def _get_chart_links(self, symbol: str, timeframe_minutes: int) -> tuple:
        """
        Generate TradingView and Coinglass links
        
        Args:
            symbol: Full symbol (e.g., BTCUSDT)
            timeframe_minutes: Timeframe in minutes (15, 30, 240)
        
        Returns:
            Tuple of (tradingview_url, coinglass_url)
        """
        # Extract clean symbol (remove USDT)
        clean_symbol = symbol.replace('USDT', '').replace('BUSD', '')
        
        # TradingView link
        tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}&interval={timeframe_minutes}"
        
        # Coinglass link
        cg_url = f"https://www.coinglass.com/pro/futures/LiquidationHeatMapNew?coin={clean_symbol}"
        
        return tv_url, cg_url
    
    def _get_ist_time(self) -> str:
        """Get current time in IST format (HH:MM:SS IST) - UTC+5:30"""
        # Convert UTC to IST (UTC + 5 hours 30 minutes)
        utc_now = datetime.utcnow()
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        return ist_now.strftime('%I:%M:%S %p IST')
    
    def format_batch_alert(self, alerts: List[dict], timeframe_minutes: int = 30) -> str:
        """
        Format multiple alerts into single batched message
        
        Args:
            alerts: List of alert dictionaries
            timeframe_minutes: Timeframe in minutes (15, 30, 240)
        
        Returns:
            Formatted batch message
        """
        if not alerts:
            return ""
        
        # Separate bullish and bearish
        bullish_alerts = [a for a in alerts if a.get('direction') == 'BULLISH']
        bearish_alerts = [a for a in alerts if a.get('direction') == 'BEARISH']
        
        total_signals = len(alerts)
        bullish_count = len(bullish_alerts)
        bearish_count = len(bearish_alerts)
        
        # Timeframe label
        if timeframe_minutes == 15:
            tf_label = "15M"
        elif timeframe_minutes == 30:
            tf_label = "30M"
        elif timeframe_minutes == 240:
            tf_label = "4H"
        else:
            tf_label = f"{timeframe_minutes}M"
        
        # Get IST time
        ist_time = self._get_ist_time()
        
        # Build message
        message = f"📊 <b>{total_signals} Gaussian Channel Signal{'s' if total_signals > 1 else ''} Detected</b>\n\n"
        message += f"🕐 {ist_time}\n\n"
        message += f"⏰ {tf_label} Primary\n\n"
        
        # Bullish section
        if bullish_alerts:
            message += "🟢 <b>Gaussian Channel - BULLISH</b>\n"
            message += "──────────────────────────────\n"
            
            for i, alert in enumerate(bullish_alerts, 1):
                symbol = alert['symbol'].replace('USDT', '')
                alert_type = alert['type']
                price = alert['close']
                
                # Determine which band was crossed
                if 'UPPER' in alert_type:
                    band_text = "Crossed above Upper Band"
                    band_value = alert['upper_band']
                elif 'LOWER' in alert_type:
                    band_text = "Crossed above Lower Band"
                    band_value = alert['lower_band']
                elif 'BOTH' in alert_type:
                    band_text = "Crossed both bands"
                    band_value = alert['upper_band']
                else:
                    band_text = "Band cross detected"
                    band_value = alert.get('upper_band', price)
                
                # Get chart links
                tv_url, cg_url = self._get_chart_links(alert['symbol'], timeframe_minutes)
                
                message += f"{i}. <b>{symbol}</b>\n"
                message += f"   {band_text}\n"
                message += f"   Price: ${price:,.2f}\n"
                message += f"   Band: ${band_value:,.2f}\n"
                message += f"   📈 <a href='{tv_url}'>Chart</a> | 🔥 <a href='{cg_url}'>Liq Heat</a>\n\n"
        
        # Bearish section
        if bearish_alerts:
            message += "🔴 <b>Gaussian Channel - BEARISH</b>\n"
            message += "──────────────────────────────\n"
            
            for i, alert in enumerate(bearish_alerts, 1):
                symbol = alert['symbol'].replace('USDT', '')
                alert_type = alert['type']
                price = alert['close']
                
                # Determine which band was crossed
                if 'LOWER' in alert_type:
                    band_text = "Crossed below Lower Band"
                    band_value = alert['lower_band']
                elif 'UPPER' in alert_type:
                    band_text = "Crossed below Upper Band"
                    band_value = alert['upper_band']
                elif 'BOTH' in alert_type:
                    band_text = "Crossed both bands"
                    band_value = alert['lower_band']
                else:
                    band_text = "Band cross detected"
                    band_value = alert.get('lower_band', price)
                
                # Get chart links
                tv_url, cg_url = self._get_chart_links(alert['symbol'], timeframe_minutes)
                
                message += f"{i}. <b>{symbol}</b>\n"
                message += f"   {band_text}\n"
                message += f"   Price: ${price:,.2f}\n"
                message += f"   Band: ${band_value:,.2f}\n"
                message += f"   📈 <a href='{tv_url}'>Chart</a> | 🔥 <a href='{cg_url}'>Liq Heat</a>\n\n"
        
        # Summary
        message += "📊 <b>Gaussian Channel Signal Summary</b>\n"
        message += f"• Total Bullish Signals: {bullish_count}\n"
        message += f"• Total Bearish Signals: {bearish_count}"
        
        return message
    
    def format_30m_alert(self, alert: dict, timeframe_minutes: int = 30) -> str:
        """
        Format single 30-minute alert (backward compatibility)
        Use format_batch_alert for multiple alerts
        """
        return self.format_batch_alert([alert], timeframe_minutes)
    
    def format_4h_alert(self, alert: dict) -> str:
        """Format single 4-hour alert (backward compatibility)"""
        return self.format_batch_alert([alert], timeframe_minutes=240)
