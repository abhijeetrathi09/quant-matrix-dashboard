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
def fetch_options_intelligence(fyers):
    """
    Risk-Adjusted Positioning Engine: Calculates Delta-Weighted PCR, 
    OI Build-Up Classification, and Trap Detection over a 30-strike window.
    """
    try:
        # 1. Fetch live Nifty Spot Price (and a simulated 'previous' for price action)
        quote_data = {"symbols": "NSE:NIFTY50-INDEX"}
        response = fyers.quotes(data=quote_data)
        
        if 'd' not in response or not response['d']:
            raise ValueError("Could not fetch Nifty Spot Price")
            
        spot_price = response['d'][0]['v']['lp']
        prev_close = response['d'][0]['v']['prev_close_price'] 
        
        # Determine intraday price action
        is_price_rising = spot_price >= prev_close
        
        # 2. Calculate the ATM Strike
        atm_strike = round(spot_price / 50) * 50
        
        # --- THE OPTIONS INTELLIGENCE ENGINE ---
        weighted_pe_oi = 0
        weighted_ce_oi = 0
        weighted_pe_oi_chg = 0
        weighted_ce_oi_chg = 0
        
        max_ce_oi = 0
        max_pe_oi = 0
        resistance_strike = atm_strike
        support_strike = atm_strike

        # Check 15 strikes up and 15 strikes down
        strikes_to_check = [atm_strike + (i * 50) for i in range(-15, 16)]
        
        # Delta Approximation Function based on Institutional Rules
        def get_approx_delta(tiers):
            if tiers == 0: return 0.50
            elif tiers == 1: return 0.40
            elif tiers == 2: return 0.30
            elif tiers <= 4: return 0.20
            elif tiers <= 9: return 0.10
            else: return 0.05

        for strike in strikes_to_check:
            distance_tiers = int(abs(strike - atm_strike) / 50)
            delta_weight = get_approx_delta(distance_tiers)
            
            # Simulated live OI data (Replace with fyers option chain pull in production)
            # Simulating institutional behavior: CE builds above ATM, PE builds below
            if strike >= atm_strike:
                ce_oi = 150000 / (distance_tiers + 1)
                pe_oi = 30000 / (distance_tiers + 1)
                ce_chg = 5000 if not is_price_rising else -2000
                pe_chg = 1000
            else:
                ce_oi = 30000 / (distance_tiers + 1)
                pe_oi = 150000 / (distance_tiers + 1)
                ce_chg = 1000
                pe_chg = 5000 if is_price_rising else -2000

            # Find dynamic Support/Resistance within the 30-strike active window
            if ce_oi > max_ce_oi:
                max_ce_oi = ce_oi
                resistance_strike = strike
            if pe_oi > max_pe_oi:
                max_pe_oi = pe_oi
                support_strike = strike

            # Apply Delta Weighting to raw OI and Change in OI
            weighted_ce_oi += (ce_oi * delta_weight)
            weighted_pe_oi += (pe_oi * delta_weight)
            weighted_ce_oi_chg += (ce_chg * delta_weight)
            weighted_pe_oi_chg += (pe_chg * delta_weight)

        # 3. Calculate Core Metrics
        true_pcr = weighted_pe_oi / weighted_ce_oi if weighted_ce_oi > 0 else 1.0
        net_weighted_oi_chg = weighted_ce_oi_chg + weighted_pe_oi_chg

        # 4. State Engine: PCR Bands
        if true_pcr > 1.3: pcr_state = "Overcrowded Longs (Extreme)"
        elif true_pcr > 1.1: pcr_state = "Bullish Zone"
        elif true_pcr >= 0.9: pcr_state = "Neutral Zone"
        elif true_pcr >= 0.7: pcr_state = "Bearish Zone"
        else: pcr_state = "Overcrowded Shorts (Extreme)"

        # 5. State Engine: Build-up Classification
        if is_price_rising and net_weighted_oi_chg > 0:
            buildup = "🟢 LONG BUILDUP"
        elif not is_price_rising and net_weighted_oi_chg > 0:
            buildup = "🔴 SHORT BUILDUP"
        elif is_price_rising and net_weighted_oi_chg < 0:
            buildup = "🟡 SHORT COVERING"
        else:
            buildup = "🟠 LONG UNWINDING"

        # 6. State Engine: Trap Detection
        trap_signal = "✅ NO TRAPS DETECTED"
        if true_pcr > 1.2 and not is_price_rising and net_weighted_oi_chg > 0:
            trap_signal = "🚨 PUT WRITERS TRAPPED (Flash Crash Risk)"
        elif true_pcr < 0.8 and is_price_rising and net_weighted_oi_chg > 0:
            trap_signal = "🚨 CALL WRITERS TRAPPED (Short Squeeze Risk)"

        return {
            "spot_price": spot_price,
            "true_pcr": round(true_pcr, 2),
            "pcr_state": pcr_state,
            "buildup": buildup,
            "trap_signal": trap_signal,
            "resistance": resistance_strike,
            "support": support_strike
        }

    except Exception as e:
        print(f"Options Engine Error: {e}")
        return {
            "spot_price": 0, "true_pcr": 1.0, "pcr_state": "Error",
            "buildup": "Error", "trap_signal": "Error",
            "resistance": 0, "support": 0
        }
