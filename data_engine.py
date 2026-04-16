# data_engine.py

from fyers_apiv3 import fyersModel
import pandas as pd
import datetime
import config
import os

def get_fyers_client():
    """Reads the daily VIP token from file and connects to Fyers."""
    if not os.path.exists("access_token.txt"):
        print("❌ Error: access_token.txt not found. Run setup_token.py first!")
        return None
        
    with open("access_token.txt", "r") as f:
        access_token = f.read().strip()
        
    return fyersModel.FyersModel(client_id=config.CLIENT_ID, is_async=False, token=access_token, log_path="")

def fetch_historical_data(fyers, symbol, days=5):
    """Fetches 5-minute candles for a specific stock."""
    data = {
        "symbol": symbol,
        "resolution": "5",
        "date_format": "1",
        "range_from": (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d"),
        "range_to": datetime.datetime.now().strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }
    
    response = fyers.history(data=data)
    
    if 'candles' not in response or not response['candles']:
        return None
        
    df = pd.DataFrame(response['candles'], columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
    df.set_index('datetime', inplace=True)
    return df