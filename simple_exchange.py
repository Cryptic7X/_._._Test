"""
Standalone Simple Exchange Manager - No Config Files Required
Uses public APIs from BingX, KuCoin, OKX for OHLCV data
"""

import requests
import time
from typing import Optional, Tuple, Dict, Any

class SimpleExchangeManager:
    def __init__(self):
        self.session = self.create_session()
        self.timeframe_mapping = {
            '15m': '15m',
            '30m': '30m', 
            '1h': '60m',
            '2h': '120m',
            '4h': '240m',
            '8h': '480m'
        }
    
    def create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'CipherB-Test/1.0',
            'Accept': 'application/json'
        })
        return session
    
    def fetch_bingx_perpetual(self, symbol: str, timeframe: str, limit: int) -> Optional[Dict]:
        """Fetch from BingX Perpetual (public API)"""
        try:
            url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
            params = {
                'symbol': symbol,
                'interval': self.timeframe_mapping.get(timeframe, '15m'),
                'limit': limit
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                candles = data['data']
                return {
                    'timestamp': [int(c['time']) for c in candles],
                    'open': [float(c['open']) for c in candles],
                    'high': [float(c['high']) for c in candles],
                    'low': [float(c['low']) for c in candles],
                    'close': [float(c['close']) for c in candles],
                    'volume': [float(c['volume']) for c in candles]
                }
            return None
        except Exception as e:
            print(f"BingX Perpetual error for {symbol}: {e}")
            return None
    
    def fetch_kucoin(self, symbol: str, timeframe: str, limit: int) -> Optional[Dict]:
        """Fetch from KuCoin (public API)"""
        try:
            # Convert timeframe to KuCoin format
            tf_map = {'15m': '15min', '30m': '30min', '1h': '1hour', '2h': '2hour', '4h': '4hour', '8h': '8hour'}
            kc_timeframe = tf_map.get(timeframe, '15min')
            
            url = "https://api.kucoin.com/api/v1/market/candles"
            params = {
                'symbol': symbol.replace('USDT', '-USDT'),
                'type': kc_timeframe
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '200000' and data.get('data'):
                candles = data['data'][:limit]
                return {
                    'timestamp': [int(c[0]) * 1000 for c in candles],  # KuCoin returns seconds
                    'open': [float(c[1]) for c in candles],
                    'high': [float(c[3]) for c in candles],
                    'low': [float(c[4]) for c in candles],
                    'close': [float(c[2]) for c in candles],
                    'volume': [float(c[5]) for c in candles]
                }
            return None
        except Exception as e:
            print(f"KuCoin error for {symbol}: {e}")
            return None
    
    def fetch_okx(self, symbol: str, timeframe: str, limit: int) -> Optional[Dict]:
        """Fetch from OKX (public API)"""
        try:
            # Convert timeframe to OKX format
            tf_map = {'15m': '15m', '30m': '30m', '1h': '1H', '2h': '2H', '4h': '4H', '8h': '8H'}
            okx_timeframe = tf_map.get(timeframe, '15m')
            
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': symbol.replace('USDT', '-USDT'),
                'bar': okx_timeframe,
                'limit': limit
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0' and data.get('data'):
                candles = data['data']
                return {
                    'timestamp': [int(c[0]) for c in candles],
                    'open': [float(c[1]) for c in candles],
                    'high': [float(c[2]) for c in candles],
                    'low': [float(c[3]) for c in candles],
                    'close': [float(c[4]) for c in candles],
                    'volume': [float(c[5]) for c in candles]
                }
            return None
        except Exception as e:
            print(f"OKX error for {symbol}: {e}")
            return None
    
    def fetch_ohlcv_with_fallback(self, symbol: str, timeframe: str, limit: int) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Fetch OHLCV with multi-exchange fallback
        Returns: (data_dict, exchange_name) or (None, None)
        """
        # Try BingX Perpetual first
        data = self.fetch_bingx_perpetual(symbol, timeframe, limit)
        if data:
            return data, "BingX Perpetual"
        
        time.sleep(0.2)  # Rate limit protection
        
        # Try KuCoin
        data = self.fetch_kucoin(symbol, timeframe, limit)
        if data:
            return data, "KuCoin"
        
        time.sleep(0.2)
        
        # Try OKX
        data = self.fetch_okx(symbol, timeframe, limit)
        if data:
            return data, "OKX"
        
        return None, None
