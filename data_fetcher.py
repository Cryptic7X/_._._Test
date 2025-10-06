import ccxt
import pandas as pd
from datetime import datetime
import time

# Initialize exchanges
def init_exchanges():
    """Initialize multiple exchanges with public APIs (excluding Binance)"""
    exchanges = {
        'kucoin': ccxt.kucoin({'enableRateLimit': True}),
        'okx': ccxt.okx({'enableRateLimit': True}),
        'bybit': ccxt.bybit({'enableRateLimit': True})
    }
    return exchanges

def fetch_ohlcv_multi_exchange(symbol, timeframe='30m', limit=100):
    """
    Fetch OHLCV data from multiple exchanges (fallback mechanism)
    Try exchanges in order: KuCoin, OKX, Bybit
    """
    exchanges = init_exchanges()
    exchange_order = ['kucoin', 'okx', 'bybit']
    
    for exchange_name in exchange_order:
        try:
            exchange = exchanges[exchange_name]
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) < 50:
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"  ✓ Data fetched from {exchange_name.upper()}: {len(df)} candles")
            return df
            
        except Exception as e:
            print(f"  ⚠ {exchange_name.upper()} failed: {str(e)}")
            continue
    
    print(f"  ✗ All exchanges failed for {symbol}")
    return None

def fetch_ohlcv_direct(exchange_name, symbol, timeframe='30m', limit=100):
    """Fetch OHLCV from specific exchange"""
    try:
        exchanges = init_exchanges()
        exchange = exchanges.get(exchange_name.lower())
        
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not supported")
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
        
    except Exception as e:
        print(f"Error fetching from {exchange_name}: {str(e)}")
        return None
