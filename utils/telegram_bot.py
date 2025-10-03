#!/usr/bin/env python3
"""
Telegram Bot for Gaussian Channel Alerts with Chart Links
"""

import os
import requests
from typing import Optional

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
    
    def format_30m_alert(self, alert: dict, timeframe_minutes: int = 30) -> str:
        """
        Format 30-minute alert message with chart links
        
        Args:
            alert: Alert dictionary
            timeframe_minutes: Timeframe in minutes (default 30, test uses 15)
        """
        symbol = alert['symbol']
        alert_type = alert['type']
        close = alert['close']
        upper = alert['upper_band']
        lower = alert['lower_band']
        direction = alert['direction']
        
        emoji = "🔥" if direction == "BULLISH" else "❄️"
        
        # Get chart links
        tv_url, cg_url = self._get_chart_links(symbol, timeframe_minutes)
        
        message = f"""
{emoji} <b>Gaussian Channel Alert [{timeframe_minutes}m]</b>

<b>Symbol:</b> {symbol}
<b>Type:</b> {alert_type.replace('_', ' ')}
<b>Direction:</b> {direction}

<b>Price:</b> ${close:.8f}
<b>Upper Band:</b> ${upper:.8f}
<b>Lower Band:</b> ${lower:.8f}

<i>The candle body has crossed the {alert_type.replace('_', ' ').lower()}</i>

📊 <a href="{tv_url}">TradingView Chart</a>
🔥 <a href="{cg_url}">Coinglass Heatmap</a>
"""
        return message.strip()
    
    def format_4h_alert(self, alert: dict) -> str:
        """Format 4-hour alert message with chart links"""
        symbol = alert['symbol']
        crossed_lines = alert['crossed_lines']
        close = alert['close']
        filter_line = alert['filter']
        upper = alert['upper_band']
        lower = alert['lower_band']
        
        lines_text = ", ".join([line.replace('_', ' ') for line in crossed_lines])
        
        # Get chart links (4h = 240 minutes)
        tv_url, cg_url = self._get_chart_links(symbol, 240)
        
        message = f"""
📊 <b>Gaussian Channel Alert [4h]</b>

<b>Symbol:</b> {symbol}
<b>Crossed:</b> {lines_text}

<b>Price:</b> ${close:.8f}
<b>Filter:</b> ${filter_line:.8f}
<b>Upper Band:</b> ${upper:.8f}
<b>Lower Band:</b> ${lower:.8f}

<i>The candle body crossed {len(crossed_lines)} line(s)</i>

📊 <a href="{tv_url}">TradingView Chart</a>
🔥 <a href="{cg_url}">Coinglass Heatmap</a>
"""
        return message.strip()
