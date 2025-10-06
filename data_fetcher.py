import ccxt
import pandas as pd
from datetime import datetime
import time

# Initialize exchanges
def init_exchanges():
    """Initialize multiple exchanges with public APIs (KuCoin and OKX only - no geo-restrictions)"""
    exchanges = {
        'kucoin': ccxt.kucoin({'enableRateLimit': True}),
        'okx': ccxt.okx({'enableRateLimit': True})
    }
    return exchanges

def format_symbol(symbol):
    """
    Format symbol to standard CCXT format (BASE/QUOTE)
    Handles: BTCUSDT -> BTC/USDT, BTC/USDT -> BTC/USDT
    """
    # If already has /, return as is
    if '/' in symbol:
        return symbol
    
    # Common quote currencies
    quote_currencies = ['USDT', 'USD', 'BUSD', 'USDC', 'BTC', 'ETH']
    
    for quote in quote_currencies:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return f"{base}/{quote}"
    
    # Default to /USDT if no quote found
    return f"{symbol}/USDT"

def fetch_ohlcv_multi_exchange(symbol, timeframe='30m', limit=100):
    """
    Fetch OHLCV data from multiple exchanges (fallback mechanism)
    Try exchanges in order: KuCoin, OKX
    """
    # Format symbol to CCXT standard
    symbol = format_symbol(symbol)
    
    exchanges = init_exchanges()
    exchange_order = ['kucoin', 'okx']
    
    for exchange_name in exchange_order:
        try:
            exchange = exchanges[exchange_name]
            
            # Load markets to check if symbol exists
            exchange.load_markets()
            
            # Check if symbol exists on this exchange
            if symbol not in exchange.markets:
                print(f"  ⚠ {exchange_name.upper()}: {symbol} not available")
                continue
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) < 50:
                print(f"  ⚠ {exchange_name.upper()}: Insufficient data ({len(ohlcv) if ohlcv else 0} candles)")
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"  ✓ Data fetched from {exchange_name.upper()}: {len(df)} candles")
            return df
            
        except ccxt.NetworkError as e:
            print(f"  ⚠ {exchange_name.upper()} network error: {str(e)[:100]}")
            continue
        except ccxt.ExchangeError as e:
            print(f"  ⚠ {exchange_name.upper()} exchange error: {str(e)[:100]}")
            continue
        except Exception as e:
            print(f"  ⚠ {exchange_name.upper()} failed: {str(e)[:100]}")
            continue
    
    print(f"  ✗ All exchanges failed for {symbol}")
    return None

def fetch_ohlcv_direct(exchange_name, symbol, timeframe='30m', limit=100):
    """Fetch OHLCV from specific exchange"""
    try:
        # Format symbol
        symbol = format_symbol(symbol)
        
        exchanges = init_exchanges()
        exchange = exchanges.get(exchange_name.lower())
        
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not supported")
        
        # Load markets
        exchange.load_markets()
        
        if symbol not in exchange.markets:
            raise ValueError(f"{symbol} not available on {exchange_name}")
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
        
    except Exception as e:
        print(f"Error fetching from {exchange_name}: {str(e)}")
        return None

def get_available_symbols(exchange_name='kucoin'):
    """Get list of all available symbols from exchange"""
    try:
        exchanges = init_exchanges()
        exchange = exchanges.get(exchange_name.lower())
        
        if not exchange:
            return []
        
        exchange.load_markets()
        symbols = list(exchange.markets.keys())
        
        # Filter USDT pairs only
        usdt_pairs = [s for s in symbols if '/USDT' in s]
        
        return usdt_pairs
        
    except Exception as e:
        print(f"Error loading markets: {str(e)}")
        return []
