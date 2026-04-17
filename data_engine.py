# data_engine.py

from fyers_apiv3 import fyersModel
import pandas as pd
import datetime
import config
import os

import streamlit as st
from fyers_apiv3 import fyersModel

def get_fyers_client():
    try:
        # Step 1: Check if we are running in the cloud and have access to the Secure Vault
        if "fyers" in st.secrets:
            client_id = st.secrets["fyers"]["client_id"]
            access_token = st.secrets["fyers"]["access_token"]
            
            # Step 2: Log in directly using the vault keys (No browser needed!)
            fyers = fyersModel.FyersModel(
                client_id=client_id, 
                is_async=False, 
                token=access_token, 
                log_path=""
            )
            return fyers
        else:
            print("No Streamlit Secrets found. Falling back to local auth...")
            return None # (Or keep your original local login code here)
            
    except Exception as e:
        print(f"Authentication Error: {e}")
        return None

# ... (Keep your fetch_historical_data function below this completely untouched!) ...

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
