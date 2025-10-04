#!/usr/bin/env python3
"""
Telegram Bot for Gaussian Channel Alerts
Batch messaging with 40 alerts per message
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List

class TelegramBot:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
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
            print(f"Telegram send error: {e}")
            return False
    
    def _get_chart_links(self, symbol: str, timeframe_minutes: int) -> tuple:
        clean_symbol = symbol.replace('USDT', '').replace('BUSD', '')
        tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}&interval={timeframe_minutes}"
        cg_url = f"https://www.coinglass.com/pro/futures/LiquidationHeatMapNew?coin={clean_symbol}"
        return tv_url, cg_url
    
    def _get_ist_time(self) -> str:
        utc_now = datetime.utcnow()
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        return ist_now.strftime('%I:%M:%S %p IST')
    
    def format_batch_alert(self, alerts: List[dict], timeframe_minutes: int = 30) -> str:
        if not alerts:
            return ""
        
        bullish_alerts = [a for a in alerts if a.get('direction') == 'BULLISH']
        bearish_alerts = [a for a in alerts if a.get('direction') == 'BEARISH']
        
        total_signals = len(alerts)
        bullish_count = len(bullish_alerts)
        bearish_count = len(bearish_alerts)
        
        tf_map = {15: "15M", 30: "30M", 240: "4H"}
        tf_label = tf_map.get(timeframe_minutes, f"{timeframe_minutes}M")
        
        ist_time = self._get_ist_time()
        
        message = f"<b>{total_signals} Gaussian Channel Signals</b>\n\n"
        message += f"Time: {ist_time}\n"
        message += f"Timeframe: {tf_label}\n\n"
        
        if bullish_alerts:
            message += "<b>BULLISH Signals</b>\n"
            message += "------------------------\n"
            
            for i, alert in enumerate(bullish_alerts, 1):
                symbol = alert['symbol'].replace('USDT', '')
                cross_method = alert.get('cross_method', 'BODY')
                price = alert['close']
                band_value = alert.get('upper_band', price)
                
                tv_url, cg_url = self._get_chart_links(alert['symbol'], timeframe_minutes)
                
                message += f"{i}. <b>{symbol}</b>\n"
                message += f"   HBand Cross ({cross_method})\n"
                message += f"   Price: ${price:,.2f}\n"
                message += f"   <a href='{tv_url}'>Chart</a> | <a href='{cg_url}'>Heat</a>\n\n"
        
        if bearish_alerts:
            message += "<b>BEARISH Signals</b>\n"
            message += "------------------------\n"
            
            for i, alert in enumerate(bearish_alerts, 1):
                symbol = alert['symbol'].replace('USDT', '')
                cross_method = alert.get('cross_method', 'BODY')
                price = alert['close']
                band_value = alert.get('lower_band', price)
                
                tv_url, cg_url = self._get_chart_links(alert['symbol'], timeframe_minutes)
                
                message += f"{i}. <b>{symbol}</b>\n"
                message += f"   LBand Cross ({cross_method})\n"
                message += f"   Price: ${price:,.2f}\n"
                message += f"   <a href='{tv_url}'>Chart</a> | <a href='{cg_url}'>Heat</a>\n\n"
        
        message += f"<b>Summary</b>\n"
        message += f"Bullish: {bullish_count} | Bearish: {bearish_count}"
        
        return message
