
import yfinance as yf
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Symbol aliases - NSE quirks
SYMBOL_FIXES = {
    "M&M": "M&M.NS",
    "MCDOWELL-N": "MCDOWELL-N.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BANKBEES": "BANKBEES.NS",
    "MID150BEES": "MID150BEES.NS",
    "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "GOLDBEES": "GOLDBEES.NS",
    "ITBEES": "ITBEES.NS",
    "MON100": "MON100.NS",
    "MOM30IETF": "MOM30IETF.NS",
}

def fetch_with_retry(symbol, retries=2):
    """Try .NS, then raw, handle no data"""
    attempts = []
    if symbol in SYMBOL_FIXES:
        attempts.append(SYMBOL_FIXES[symbol])
    attempts.append(f"{symbol}.NS")
    attempts.append(symbol) # raw
    
    for ticker in attempts:
        try:
            for _ in range(retries):
                hist = yf.Ticker(ticker).history(period="1d", interval="15m", timeout=10)
                if not hist.empty and len(hist) >= 3 and hist['Volume'].sum() > 0:
                    return hist, ticker
                time.sleep(0.5)
        except Exception as e:
            continue
    return None, None

def get_features_robust(symbol):
    hist, used_ticker = fetch_with_retry(symbol)
    if hist is None:
        return None, f"NO_DATA ({symbol}) - tried {SYMBOL_FIXES.get(symbol, symbol+'.NS')}"
    
    try:
        ltp = hist['Close'].iloc[-1]
        vwap = (hist['Close'] * hist['Volume']).sum() / (hist['Volume'].sum() + 1)
        or_high = hist['High'].iloc[0:2].max()
        or_low = hist['Low'].iloc[0:2].min()
        
        # Filter low price / illiquid
        if ltp < 20: # penny
            return None, f"LOW_PRICE {ltp}"
        
        # Score
        if ltp > vwap and ltp > or_high:
            return {
                "symbol": symbol,
                "used_ticker": used_ticker,
                "score": 82,
                "setup": "ORB Breakout",
                "rs": 1.3,
                "vol": 2.0,
                "vwap_dist": round((ltp-vwap)/vwap*100,2),
                "entry": round(ltp,2),
                "sl": round(min(or_low, vwap*0.995),2),
                "target": round(ltp*1.015,2),
                "risk": 0.5,
                "sentiment": 1
            }, "OK"
        return None, f"NO_SETUP ltp {ltp:.1f} vwap {vwap:.1f}"
    except Exception as e:
        return None, f"ERROR {e}"

def scan_robust(universe, max_workers=12):
    results = []
    no_data = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {ex.submit(get_features_robust, s): s for s in universe}
        for f in as_completed(fut):
            feat, reason = f.result()
            if feat:
                results.append(feat)
            else:
                if "NO_DATA" in reason:
                    no_data.append(reason)
    return sorted(results, key=lambda x: x['score'], reverse=True)[:5], no_data
