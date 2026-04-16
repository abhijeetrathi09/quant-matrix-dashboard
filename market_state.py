# market_state.py

import streamlit as st
import json
import time
import os
import pandas as pd
from datetime import datetime, time as dt_time
import config
import data_engine
import math_engine
import logic_engine

st.set_page_config(page_title="Prop Desk Engine", layout="wide")

# --- AUTO-ADAPTING GRID CSS ---
st.markdown("""
    <style>
    .metric-box { padding: 15px; border-radius: 8px; background-color: rgba(128, 128, 128, 0.1); margin-bottom: 10px; border-left: 5px solid; height: 95%; }
    .title-text { font-size: 12px; color: #888; text-transform: uppercase; font-weight: 800; margin-bottom: 4px; letter-spacing: 0.5px;}
    .subtitle-text { font-size: 11px; color: #777; margin-bottom: 8px;}
    .value-text { font-size: 26px; font-weight: 800; margin: 0; line-height: 1.1;}
    .status-text { font-size: 15px; font-weight: 800; margin-top: 5px; text-transform: uppercase; }
    .block-container { padding-top: 1.5rem; }
    header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- STRICT DATA COLORS ---
COLOR_BULL = "#00C805" 
COLOR_BEAR = "#FF3333" 
COLOR_NEUT = "#FFA500" 

# --- WEIGHT LOADER CACHING ---
@st.cache_data
def load_stock_weights():
    try:
        df_weights = pd.read_csv("weights.csv") 
        df_weights.columns = df_weights.columns.str.strip()
        if 'Weight' in df_weights.columns:
            if df_weights['Weight'].dtype == object:
                df_weights['Weight'] = df_weights['Weight'].astype(str).str.replace(',', '')
            df_weights['Weight'] = pd.to_numeric(df_weights['Weight'], errors='coerce').fillna(0)
        else: raise KeyError("Could not find a column exactly named 'Weight'")
            
        raw_weights = dict(zip(df_weights['Symbol'], df_weights['Weight']))
        total_weight = sum(raw_weights.values())
        if total_weight == 0: raise ValueError("All weights calculated to 0.")
            
        return {sym: (w / total_weight) for sym, w in raw_weights.items()}
    except Exception as e:
        return None 

# --- UI HELPER ---
def draw_metric(title, subtitle, value, color_override=None, is_pct=True):
    color = color_override if color_override else (COLOR_BULL if value > 55 else COLOR_BEAR if value < 45 else COLOR_NEUT)
    display_val = f"{value:.1f}" if isinstance(value, (int, float)) and is_pct else f"{value}"
    html = f"""
    <div class="metric-box" style="border-color: {color};">
        <div class="title-text">{title}</div>
        <div class="subtitle-text">{subtitle}</div>
        <div class="value-text">{display_val}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if is_pct and isinstance(value, (int, float)):
        st.progress(int(value) / 100 if value <= 100 else 1.0)

# --- INITIALIZATION & MEMORY ---
if 'history_loaded' not in st.session_state:
    st.session_state.history_loaded = False
    st.session_state.base_data = {}

if not st.session_state.history_loaded:
    st.title("🧠 Institutional Quant Terminal")
    if st.button("Initialize Quant Engine", type="primary"):
        st.info("⏳ Connecting to Fyers Vault & Loading Equities...") 
        try:
            fyers = data_engine.get_fyers_client()
            if fyers:
                st.success("✅ Fyers Connected!")
                bar = st.progress(0, "Crunching institutional data...")
                for i, sym in enumerate(config.NIFTY_SYMBOLS):
                    df = data_engine.fetch_historical_data(fyers, sym, days=5)
                    if df is not None and not df.empty:
                        st.session_state.base_data[sym] = math_engine.calculate_indicators(df)
                    bar.progress((i + 1) / len(config.NIFTY_SYMBOLS))
                st.session_state.history_loaded = True
                st.session_state.fyers_client = fyers # Save connection for live loop
                st.rerun()
            else:
                st.error("❌ Fyers refused connection. Check your Streamlit Secrets vault!")
        except Exception as e:
            st.error(f"🚨 CRASH inside data_engine.py: {e}")

# --- LIVE ENGINE LOOP ---
if st.session_state.history_loaded:
    fyers = st.session_state.get('fyers_client', None)
    
    # --- TABS SETUP ---
    tab_equity, tab_options = st.tabs(["🧠 EQUITY MATRIX", "⛓️ OPTIONS INTELLIGENCE"])

    # ==========================================
    #       TAB 1: EQUITY MATRIX
    # ==========================================
    with tab_equity:
        live_data = {}
        if os.path.exists("live_prices.json"):
            try:
                with open("live_prices.json", "r") as f: live_data = json.load(f)
            except: pass

        weights = load_stock_weights()
        above_vwap_wt = below_vwap_wt = above_20_ema_wt = 0.0
        macd_bull_wt = rsi_hot_wt = rsi_cold_wt = 0.0
        adv_wt = dec_wt = vol_strong_wt = atr_expand_wt = 0.0
        total_valid_weight = 0.0 
        
        for sym, df in st.session_state.base_data.items():
            if len(df) < 2: continue
            w = weights.get(sym, 0.0) if weights else 1.0 
            total_valid_weight += w
            
            last, prev = df.iloc[-1], df.iloc[-2]
            current_price = live_data.get(sym, last['close'])
            
            if current_price > last['VWAP']: above_vwap_wt += w
            else: below_vwap_wt += w
            if current_price > last['EMA_20']: above_20_ema_wt += w
            if last['MACD_Line'] > last['MACD_Signal']: macd_bull_wt += w
            if last['RSI'] > 60: rsi_hot_wt += w
            elif last['RSI'] < 40: rsi_cold_wt += w
            if current_price > prev['close']: adv_wt += w
            elif current_price < prev['close']: dec_wt += w
            if last['volume'] > last['Volume_Avg_20']: vol_strong_wt += w
            if last['ATR_Expanding']: atr_expand_wt += w

        pct_vwap = (above_vwap_wt / total_valid_weight) * 100
        pct_ema = (above_20_ema_wt / total_valid_weight) * 100
        pct_macd = (macd_bull_wt / total_valid_weight) * 100
        pct_rsi_hot = (rsi_hot_wt / total_valid_weight) * 100
        pct_rsi_cold = (rsi_cold_wt / total_valid_weight) * 100
        pct_vol = (vol_strong_wt / total_valid_weight) * 100
        pct_atr = (atr_expand_wt / total_valid_weight) * 100
        total_ad_wt = adv_wt + dec_wt
        pct_ad = (adv_wt / total_ad_wt * 100) if total_ad_wt > 0 else 50.0

        S, M, P, V, master_score = logic_engine.calculate_core_scores(
            pct_vwap, pct_ema, pct_macd, pct_rsi_hot, pct_rsi_cold, pct_ad, pct_vol, pct_atr
        )
        summary_template, m_score, bias, conf, mode = logic_engine.generate_summary(S, M, P, V, master_score)

        top_left, top_right = st.columns([1.5, 1])
        with top_left:
            st.markdown("<h2 style='margin-top: 0; padding-top: 0;'>🧠 Institutional Equity Matrix</h2>", unsafe_allow_html=True)
            st.info(summary_template)
            
        with top_right:
            comp_color = COLOR_BULL if m_score > 60 else COLOR_BEAR if m_score < 40 else COLOR_NEUT
            st.markdown(f"""
            <div class="metric-box" style="border-color: {comp_color}; padding: 18px;">
                <div class="title-text" style="font-size: 14px;">🧠 Master Engine Score</div>
                <div class="subtitle-text">Bias: {bias} | Conf: {conf}</div>
                <div class="value-text" style="font-size: 50px;">{m_score:.1f}</div>
                <div class="status-text" style="color: {comp_color};">{mode}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        r2_1, r2_2, r2_3, r2_4 = st.columns(4)
        with r2_1: draw_metric("🟢 STR: Trend Convict", f"> 20 EMA ({pct_ema:.1f}%)", pct_ema)
        with r2_2: draw_metric("🟡 PART: VWAP Control", f"Intraday ({pct_vwap:.1f}%)", pct_vwap)
        with r2_3: draw_metric("🟡 PART: A/D Strength", f"Adv/Dec ({pct_ad:.1f}%)", pct_ad)
        with r2_4: draw_metric("🟡 PART: Vol Confirm", f"Vol Surges ({pct_vol:.1f}%)", pct_vol)

        r3_1, r3_2, r3_3, r3_4 = st.columns(4)
        with r3_1: draw_metric("🔵 MOM: MACD Bullish", f"Breadth ({pct_macd:.1f}%)", pct_macd)
        with r3_2: draw_metric("🔵 MOM: RSI > 60", f"Hot Weight ({pct_rsi_hot:.1f}%)", pct_rsi_hot, COLOR_BULL)
        with r3_3: draw_metric("🔵 MOM: RSI < 40", f"Cold Weight ({pct_rsi_cold:.1f}%)", pct_rsi_cold, COLOR_BEAR)
        with r3_4: 
            v_color = COLOR_BEAR if V > 60 else COLOR_BULL if V < 40 else COLOR_NEUT
            draw_metric("🔴 VOL: ATR Expand", f"Range Expansion ({V:.1f}%)", V, v_color)

    # ==========================================
    #       TAB 2: OPTIONS INTELLIGENCE
    # ==========================================
    with tab_options:
        if fyers:
            intel = data_engine.fetch_options_intelligence(fyers)
        else:
            intel = {"spot_price": 0, "true_pcr": 1.0, "pcr_state": "Offline", "buildup": "Offline", "trap_signal": "Offline", "resistance": 0, "support": 0}

        st.markdown(f"### 🧠 Risk-Adjusted Positioning Engine (Spot: {intel['spot_price']})")
        
        if "🚨" in intel['trap_signal']:
            st.error(f"**DANGER:** {intel['trap_signal']}")
        else:
            st.success(f"**STATUS:** {intel['trap_signal']}")

        st.markdown("<br>", unsafe_allow_html=True)
        
        o1, o2, o3, o4 = st.columns(4)
        
        with o1:
            pcr_color = COLOR_BEAR if intel['true_pcr'] < 0.9 or intel['true_pcr'] > 1.3 else COLOR_BULL if intel['true_pcr'] > 1.1 else COLOR_NEUT
            draw_metric("📊 TRUE PCR (Δ)", intel['pcr_state'], intel['true_pcr'], pcr_color, is_pct=False)
            
        with o2:
            build_color = COLOR_BULL if "LONG BUILDUP" in intel['buildup'] else COLOR_BEAR if "SHORT BUILDUP" in intel['buildup'] else COLOR_NEUT
            st.markdown(f"""
            <div class="metric-box" style="border-color: {build_color};">
                <div class="title-text">SMART MONEY FLOW</div>
                <div class="subtitle-text">Price + Weighted OI Chg</div>
                <div class="status-text" style="color: {build_color}; font-size: 18px;">{intel['buildup']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with o3:
            draw_metric("🛑 RESISTANCE", "Max Call OI (Active Zone)", intel['resistance'], COLOR_BEAR, is_pct=False)
            
        with o4:
            draw_metric("🟢 SUPPORT", "Max Put OI (Active Zone)", intel['support'], COLOR_BULL, is_pct=False)

    # ==========================================
    #       MARKET HOURS & DATA EXPORTER
    # ==========================================
    now = datetime.now()
    current_time_only = now.time()
    
    # 09:15 AM to 03:30 PM
    market_start = dt_time(9, 15)
    market_end = dt_time(15, 30)
    is_market_open = (market_start <= current_time_only <= market_end)

    if is_market_open:
        current_minute = now.minute

        if 'last_export_minute' not in st.session_state:
            st.session_state.last_export_minute = current_minute

        if current_minute != st.session_state.last_export_minute:
            export_file = "quant_score_history.csv"
            
            _, conf_pts = logic_engine.calculate_confidence(S, M, P, V)
            market_state, _, _ = logic_engine.determine_market_state_and_mode(S, M, P, V, conf_pts)
            
            export_df = pd.DataFrame([{
                "Timestamp": now.strftime("%Y-%m-%d %H:%M:00"),
                "Structure (S)": round(S, 2),
                "Momentum (M)": round(M, 2),
                "Participation (P)": round(P, 2),
                "Volatility (V)": round(V, 2),
                "Master Score": round(m_score, 2),
                "Market State": market_state,
                "Bias": bias,
                "Confidence": conf,
                "Trade Mode": mode
            }])
            
            if not os.path.exists(export_file):
                export_df.to_csv(export_file, index=False)
            else:
                export_df.to_csv(export_file, mode='a', header=False, index=False)
                
            st.session_state.last_export_minute = current_minute

        time.sleep(2)
        st.rerun()
    else:
        st.warning("⏸️ **Market is Closed.** Engine and data export are paused until 09:15 AM. Refresh the page to restart.")
        st.stop()
