
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Momentum + High RR config
MIN_RR = 2.5  # You asked higher RR, not 2R
MIN_MOMENTUM_PCT = 0.8  # must be up 0.8% intraday minimum
MIN_BETA = 1.1

SYMBOL_FIXES = {
    "M&M": "M&M.NS", "MCDOWELL-N": "MCDOWELL-N.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BANKBEES": "BANKBEES.NS", "MID150BEES": "MID150BEES.NS", "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS", "GOLDBEES": "GOLDBEES.NS", "SILVERBEES": "SILVERBEES.NS",
    "ITBEES": "ITBEES.NS", "PSUBNKBEES": "PSUBNKBEES.NS", "PHARMABEES": "PHARMABEES.NS",
    "MOM30IETF": "MOM30IETF.NS", "MID150MOM50": "MID150MOM50.NS", "MON100": "MON100.NS",
    "MAFANG": "MAFANG.NS", "ALPHAIETF": "ALPHAIETF.NS", "CPSEBEES": "CPSEBEES.NS",
}

def fetch_robust(symbol):
    attempts = [SYMBOL_FIXES.get(symbol, f"{symbol}.NS"), f"{symbol}.NS", symbol]
    for ticker in attempts:
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="15m", timeout=10)
            if not hist.empty and len(hist) >= 10 and hist['Volume'].iloc[-5:].sum() > 0:
                return hist, ticker
        except: continue
    return None, None

def momentum_score(hist):
    """Score momentum for high RR"""
    try:
        # 15m momentum: last 3 candles vs previous
        recent = hist['Close'].iloc[-3:].mean()
        prev = hist['Close'].iloc[-6:-3].mean()
        intraday_change = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
        momentum = (recent / prev - 1) * 100
        
        # Volume confirmation
        vol_recent = hist['Volume'].iloc[-3:].mean()
        vol_avg = hist['Volume'].iloc[-10:-3].mean()
        vol_ratio = vol_recent / (vol_avg + 1)
        
        return intraday_change, momentum, vol_ratio
    except:
        return 0, 0, 0

def get_high_rr_setup(symbol):
    hist, used = fetch_robust(symbol)
    if hist is None:
        return None
    
    ltp = float(hist['Close'].iloc[-1])
    if ltp < 20: return None # ignore penny
    
    # VWAP
    vwap = float((hist['Close'] * hist['Volume']).sum() / (hist['Volume'].sum() + 1))
    or_high = float(hist['High'].iloc[0:2].max())
    or_low = float(hist['Low'].iloc[0:2].min())
    
    intraday_chg, mom, vol_ratio = momentum_score(hist)
    
    # FILTERS FOR HIGH RR + MOMENTUM (your priority)
    if intraday_chg < 0.8: return None # no momentum
    if mom < 0.3: return None # not accelerating
    if vol_ratio < 1.8: return None # no volume
    if ltp < vwap: return None # below VWAP
    if ltp < or_high: return None # not breaking OR
    
    # High RR calculation - wide target, tight SL
    sl = min(or_low, vwap * 0.997) # tight SL
    risk = ltp - sl
    if risk <= 0: return None
    risk_pct = (risk / ltp) * 100
    if risk_pct > 1.0 or risk_pct < 0.2: return None # risk too high or too low
    
    target = ltp + risk * 3.0 # 3R target - HIGH RR as you asked
    
    # Momentum boost for ETFs with high beta
    score = 0
    score += 30 if intraday_chg > 1.5 else 15
    score += 25 if mom > 0.8 else 10
    score += 20 if vol_ratio > 2.5 else 10
    score += 15 if ltp > or_high * 1.002 else 5
    score += 10  # above VWAP
    
    # ETF bonus for high beta
    if "BEES" in symbol or symbol in ["MON100","MAFANG"]:
        score += 5
    
    if score < 75: return None
    
    return {
        "symbol": symbol,
        "ticker": used,
        "score": int(min(score, 99)),
        "setup": "High-Momentum ORB" if mom > 0.8 else "VWAP Momentum",
        "ltp": round(ltp,2),
        "intraday_chg": round(intraday_chg,2),
        "momentum": round(mom,2),
        "vol": round(vol_ratio,1),
        "vwap_dist": round((ltp-vwap)/vwap*100,2),
        "entry": round(ltp,2),
        "sl": round(sl,2),
        "target": round(target,2),
        "risk_pct": round(risk_pct,2),
        "rr": 3.0,
        "reward_pct": round(risk_pct * 3.0,2)
    }

def scan_high_rr(universe, max_workers=15):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {ex.submit(get_high_rr_setup, s): s for s in universe}
        for f in as_completed(fut):
            try:
                res = f.result()
                if res: results.append(res)
            except: pass
    # Sort by momentum + RR
    return sorted(results, key=lambda x: (x['intraday_chg'] + x['momentum'] + x['vol']), reverse=True)[:5]
