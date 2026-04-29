"""
Market Configuration
Define all markets to trade
"""

MARKETS = {
    # INDIAN STOCKS (NSE)
    'indian_stocks': {
        'enabled': True,
        'symbols': [
            'RELIANCE.NS',    # Reliance Industries
            'TCS.NS',         # Tata Consultancy Services
            'HDFCBANK.NS',    # HDFC Bank
            'INFY.NS',        # Infosys
            'HINDUNILVR.NS',  # Hindustan Unilever
            'ICICIBANK.NS',   # ICICI Bank
            'SBIN.NS',        # State Bank of India
            'BHARTIARTL.NS',  # Bharti Airtel
            'ITC.NS',         # ITC Limited
            'LT.NS'           # Larsen & Toubro
        ],
        'source': 'yahoo',
        'capital_allocation': 0.30  # 30% of capital
    },
    
    # US STOCKS
    'us_stocks': {
        'enabled': True,
        'symbols': [
            'AAPL',   # Apple
            'MSFT',   # Microsoft
            'GOOGL',  # Google
            'TSLA',   # Tesla
            'NVDA',   # NVIDIA
            'META',   # Meta
            'AMZN'    # Amazon
        ],
        'source': 'yahoo',
        'capital_allocation': 0.30  # 30% of capital
    },
    
    # CRYPTOCURRENCY
    'crypto': {
        'enabled': True,
        'symbols': [
            'BTC-USD',    # Bitcoin
            'ETH-USD',    # Ethereum
            'SOL-USD',    # Solana
            'BNB-USD',    # Binance Coin
            'ADA-USD'     # Cardano
        ],
        'source': 'yahoo',
        'capital_allocation': 0.25  # 25% of capital
    },
    
    # INDICES (for trend confirmation)
    'indices': {
        'enabled': True,
        'symbols': [
            '^NSEI',   # NIFTY 50
            '^BSESN',  # SENSEX
            '^NSEBANK', # BANKNIFTY
            '^GSPC',   # S&P 500
            '^DJI'     # Dow Jones
        ],
        'source': 'yahoo',
        'capital_allocation': 0.15  # 15% of capital
    }
}

def get_all_tradeable_symbols():
    """Get all symbols to trade"""
    symbols = []
    
    for market_type, config in MARKETS.items():
        if config['enabled']:
            symbols.extend(config['symbols'])
    
    return symbols

def get_capital_allocation(symbol):
    """Get capital allocation for a symbol"""
    for market_type, config in MARKETS.items():
        if symbol in config['symbols']:
            return config['capital_allocation']
    
    return 0.25  # Default 25%

def get_data_source(symbol):
    """Get data source for a symbol"""
    for market_type, config in MARKETS.items():
        if symbol in config['symbols']:
            return config['source']
    
    return 'yahoo'  # Default