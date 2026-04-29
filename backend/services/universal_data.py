"""
Universal Data Provider
Supports multiple data sources for different markets
"""
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta

class UniversalDataProvider:
    def __init__(self):
        self.sources = {
            'yahoo': self._fetch_yahoo,
            'nse': self._fetch_nse,
            'tradingview': self._fetch_tradingview
        }
    
    def get_data(self, symbol, source='auto', period=50):
        """
        Get OHLCV data from best available source
        
        Args:
            symbol: Ticker (e.g., 'RELIANCE.NS', 'BTC-USD', 'AAPL')
            source: 'auto', 'yahoo', 'nse', 'tradingview'
            period: Number of candles
        """
        if source == 'auto':
            source = self._detect_source(symbol)
        
        fetcher = self.sources.get(source, self._fetch_yahoo)
        return fetcher(symbol, period)
    
    def _detect_source(self, symbol):
        """Auto-detect best source based on symbol"""
        if '.NS' in symbol or '.BO' in symbol:
            return 'yahoo'  # Indian stocks
        elif '-' in symbol:
            return 'yahoo'  # Crypto (BTC-USD format)
        else:
            return 'yahoo'  # Default to Yahoo
    
    def _fetch_yahoo(self, symbol, period):
        """Fetch from Yahoo Finance (works for most markets)"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f'{period}d', interval='1d')
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
            return pd.DataFrame()
    
    def _fetch_nse(self, symbol, period):
        """Fetch from NSE (Indian stocks - real-time)"""
        try:
            # NSE API endpoint (example - may need updates)
            base_url = "https://www.nseindia.com/api/historical/cm/equity"
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
            
            # Clean symbol (remove .NS)
            clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period)
            
            params = {
                'symbol': clean_symbol,
                'from': start_date.strftime('%d-%m-%Y'),
                'to': end_date.strftime('%d-%m-%Y')
            }
            
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Parse NSE JSON response into DataFrame
                # (Implementation depends on NSE API structure)
                return pd.DataFrame()  # Placeholder
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"NSE error for {symbol}: {e}")
            return self._fetch_yahoo(symbol, period)  # Fallback
    
    def _fetch_tradingview(self, symbol, period):
        """
        Fetch from TradingView (requires web scraping or unofficial API)
        Note: This is a placeholder - TradingView scraping requires
        more complex implementation
        """
        print(f"TradingView fetch not yet implemented for {symbol}")
        return self._fetch_yahoo(symbol, period)  # Fallback
    
    def get_realtime_price(self, symbol):
        """Get current price (real-time)"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if not data.empty:
                return float(data['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            print(f"Real-time price error for {symbol}: {e}")
            return None