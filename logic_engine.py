# logic_engine.py

def calculate_core_scores(pct_vwap, pct_ema, pct_macd, pct_rsi_hot, pct_rsi_cold, pct_ad, pct_vol, pct_atr):
    """NORMALIZE EVERYTHING TO WEIGHTED 0-100"""
    
    # Structure (S) -> Now purely Trend/EMA based
    S = pct_ema
    
    # Momentum (M) -> Weighted MACD + RSI
    rsi_bullish = 50 + (pct_rsi_hot / 2) - (pct_rsi_cold / 2)
    M = (pct_macd + rsi_bullish) / 2.0
    
    # Participation (P) -> Now includes VWAP + AD + Volume Conviction
    P = (pct_vwap + pct_ad + pct_vol) / 3.0
    
    # Volatility (V) -> ATR Expansion Breadth
    V = pct_atr

    # UPDATED MASTER SCORE FORMULA (Weighted Architecture)
    # 0.30(S) + 0.25(P) + 0.25(M) + 0.20(V)
    master_score = (0.30 * S) + (0.25 * P) + (0.25 * M) + (0.20 * V)
    
    return S, M, P, V, master_score


def get_market_internals(S, M, P, V):
    """4-7. DIRECTION, ALIGNMENT, PARTICIPATION, VOLATILITY REGIMES"""
    bias = "BULLISH" if S > 50 else "BEARISH"
    
    struct_str = "Strong Bullish" if S > 60 else "Strong Bearish" if S < 40 else "Neutral/Mixed"
    mom_str = "Aligned" if (S > 60 and M > 55) or (S < 40 and M < 45) else "Diverging"
    part_str = "Strong" if P > 60 else "Moderate" if P >= 45 else "Weak"
    vol_str = "Expansion" if V > 60 else "Compression" if V < 40 else "Normal"
    
    return bias, struct_str, mom_str, part_str, vol_str

def calculate_confidence(S, M, P, V):
    """8. CONFIDENCE ENGINE"""
    points = 0
    if (S > 50 and M > 50) or (S < 50 and M < 50): points += 1 # Momentum aligned
    if P > 50: points += 1                                     # Participation confirms
    if V > 50 or V < 40: points += 1                           # Vol supports move OR confirms compression

    if points == 3: return "HIGH", 3
    elif points == 2: return "MEDIUM", 2
    elif points == 1: return "LOW", 1
    else: return "VERY LOW", 0

def determine_market_state_and_mode(S, M, P, V, confidence_pts):
    """3 & 9. MARKET STATE CLASSIFICATION & TRADE MODE ENGINE"""
    # STATE 4 - EXHAUSTION
    if (S < 20 or S > 80) and ((S > 50 and M < S) or (S < 50 and M > S)) and P < 50:
        return "EXHAUSTION", "MEAN REVERSION MODE", "Fade moves. Look for reversal setups."
    
    # STATE 1 - STRONG TREND
    if (S > 65 or S < 35) and ((S > 50 and M > 50) or (S < 50 and M < 50)) and P > 55:
        if confidence_pts >= 2:
            return "STRONG TREND", "TREND MODE", "Trade in direction. Look for pullback entries."
        
    # STATE 2 - WEAK TREND
    if (S > 60 or S < 40) and P < 50:
        return "WEAK TREND", "CAUTION MODE", "Fake moves / traps likely. Reduce size."
        
    # STATE 3 - COMPRESSION
    if 40 <= S <= 60 and V < 40:
        return "COMPRESSION", "BREAKOUT MODE", "Wait for breakout. No early entries."
        
    # STATE 5 - CHAOTIC
    return "CHAOTIC / NO TRADE", "NO TRADE MODE", "Stay out. Mixed signals."

def generate_summary(S, M, P, V, master_score):
    """10. FINAL SUMMARY GENERATOR"""
    bias, struct_str, mom_str, part_str, vol_str = get_market_internals(S, M, P, V)
    conf_label, conf_pts = calculate_confidence(S, M, P, V)
    state, mode, action = determine_market_state_and_mode(S, M, P, V, conf_pts)
    
    # Ensure color coding for UI
    mode_color = "🟢" if "TREND" in mode else "🔵" if "BREAKOUT" in mode else "🟡" if "REVERSION" in mode else "🔴"

    template = f"""
**Market State:** {state}  
**Bias:** {bias}  
**Confidence:** {conf_label}  

* **Structure:** {struct_str} ({S:.1f}%)  
* **Momentum:** {mom_str} ({M:.1f}%)  
* **Participation:** {part_str} ({P:.1f}%)  
* **Volatility:** {vol_str} ({V:.1f}%)  

#### {mode_color} → Trade Mode: {mode}
**→ Action:** {action}
"""
    return template, master_score, bias, conf_label, mode