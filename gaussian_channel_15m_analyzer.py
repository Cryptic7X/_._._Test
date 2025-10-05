"""
Gaussian Channel 15-Minute Analyzer
Detects band crossing events for multiple coins
"""

import ccxt
import pandas as pd
from datetime import datetime
from gaussian_channel import GaussianChannel


class GaussianChannel15mAnalyzer:
    """
    15-minute Gaussian Channel analyzer with band crossing detection
    
    Alert Types:
    1. HBand Cross ↑ (from below) - BULLISH
    2. HBand Cross ↓ (from above) - BEARISH
    3. LBand Cross ↓ (from above) - BEARISH
    4. LBand Cross ↑ (from below) - BULLISH
    """
    
    def __init__(self):
        self.gc = GaussianChannel(poles=4, period=144, tr_multiplier=1.414, 
                                   reduced_lag=True, fast_response=False)
        self.timeframe = '15m'
        self.exchanges = ['kucoin', 'okx', 'bybit']
        
    def format_symbol(self, coin, exchange_name):
        """
        Convert BTCUSDT format to exchange-specific format
        
        Args:
            coin: Coin symbol (e.g., 'BTCUSDT')
            exchange_name: Exchange name ('kucoin', 'okx', 'bybit')
        
        Returns:
            Formatted symbol (e.g., 'BTC/USDT')
        """
        if coin.endswith('USDT'):
            base = coin[:-4]
            return f"{base}/USDT"
        return coin
    
    def fetch_data(self, symbol, exchange_name, limit=300):
        """
        Fetch 15-minute OHLCV data from specified exchange
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange_name: Exchange name
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            exchange_class = getattr(ccxt, exchange_name)
            exchange_obj = exchange_class()
            
            ohlcv = exchange_obj.fetch_ohlcv(symbol, self.timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) < 200:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            return None
    
    def fetch_data_with_fallback(self, coin):
        """
        Try fetching data from multiple exchanges with fallback
        
        Args:
            coin: Coin symbol (e.g., 'BTCUSDT')
        
        Returns:
            tuple: (DataFrame, exchange_name) or (None, None)
        """
        for exchange_name in self.exchanges:
            try:
                symbol = self.format_symbol(coin, exchange_name)
                df = self.fetch_data(symbol, exchange_name)
                
                if df is not None:
                    return df, exchange_name
                    
            except Exception:
                continue
        
        return None, None
    
    def detect_band_cross(self, curr_row, prev_row):
        """
        Detect band CROSSING events
        
        Returns:
            tuple: (band, direction) or None
            - band: 'hband' or 'lband'
            - direction: 'from_below' or 'from_above'
        """
        # Current candle
        curr_high = curr_row['high']
        curr_low = curr_row['low']
        curr_upper = curr_row['upper_band']
        curr_lower = curr_row['lower_band']
        
        # Previous candle
        prev_high = prev_row['high']
        prev_low = prev_row['low']
        prev_upper = prev_row['upper_band']
        prev_lower = prev_row['lower_band']
        
        # Previous candle position
        prev_above_upper = prev_low > prev_upper
        prev_below_lower = prev_high < prev_lower
        prev_inside = not prev_above_upper and not prev_below_lower
        
        # Check crosses
        
        # HBand cross from below (BULLISH)
        if (prev_inside or prev_below_lower) and curr_high >= curr_upper:
            return ('hband', 'from_below')
        
        # HBand cross from above (BEARISH)
        if prev_above_upper and curr_low <= curr_upper:
            return ('hband', 'from_above')
        
        # LBand cross from above (BEARISH)
        if (prev_inside or prev_above_upper) and curr_low <= curr_lower:
            return ('lband', 'from_above')
        
        # LBand cross from below (BULLISH)
        if prev_below_lower and curr_high >= curr_lower:
            return ('lband', 'from_below')
        
        return None
    
    def analyze_coin(self, coin):
        """
        Analyze single coin for band crossing signals
        
        Args:
            coin: Coin symbol (e.g., 'BTCUSDT')
        
        Returns:
            dict with analysis results or None if no signal
        """
        # Fetch data with fallback
        df, exchange_used = self.fetch_data_with_fallback(coin)
        
        if df is None:
            return None
        
        # Calculate Gaussian Channel
        df = self.gc.calculate(df)
        
        # Get last two candles
        curr_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        curr_time = df.index[-1]
        
        # Detect band cross
        cross_result = self.detect_band_cross(curr_row, prev_row)
        
        if cross_result is None:
            return None
        
        band, direction = cross_result
        
        # Determine signal type
        if band == 'hband':
            signal_type = 'BULLISH' if direction == 'from_below' else 'BEARISH'
            band_value = curr_row['upper_band']
        else:
            signal_type = 'BEARISH' if direction == 'from_above' else 'BULLISH'
            band_value = curr_row['lower_band']
        
        return {
            'coin': coin,
            'band': band,
            'direction': direction,
            'signal': signal_type,
            'timestamp': curr_time,
            'close': curr_row['close'],
            'band_value': band_value,
            'filter': curr_row['filter'],
            'exchange': exchange_used
        }
