
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

SYMBOL_FIXES = {
    "M&M": "M&M.NS", "MCDOWELL-N": "MCDOWELL-N.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BANKBEES": "BANKBEES.NS", "MID150BEES": "MID150BEES.NS", "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS", "GOLDBEES": "GOLDBEES.NS", "SILVERBEES": "SILVERBEES.NS",
    "ITBEES": "ITBEES.NS", "PSUBNKBEES": "PSUBNKBEES.NS", "PHARMABEES": "PHARMABEES.NS",
    "MOM30IETF": "MOM30IETF.NS", "MID150MOM50": "MID150MOM50.NS", "MON100": "MON100.NS",
    "MAFANG": "MAFANG.NS", "ALPHAIETF": "ALPHAIETF.NS", "CPSEBEES": "CPSEBEES.NS",
}

def fetch_multi_timeframe(symbol):
    """Get 1d 15m + 10d daily for volume comparison"""
    ticker_str = SYMBOL_FIXES.get(symbol, f"{symbol}.NS")
    try:
        t = yf.Ticker(ticker_str)
        # Intraday 15m today
        intraday = t.history(period="5d", interval="15m", timeout=15)
        # Daily for 10 days volume comparison
        daily = t.history(period="20d", interval="1d", timeout=15)
        if intraday.empty or daily.empty or len(daily) < 6:
            return None, None, ticker_str
        return intraday, daily, ticker_str
    except:
        return None, None, ticker_str

def momentum_volume_score(symbol):
    intraday, daily, used = fetch_multi_timeframe(symbol)
    if intraday is None or daily is None:
        return None
    
    try:
        ltp = float(intraday['Close'].iloc[-1])
        if ltp < 25: return None
        
        # --- VOLUME ANALYSIS vs Previous Days ---
        today_vol_so_far = float(intraday['Volume'].iloc[-8:].sum())  # last ~2 hours in 15m
        # Daily volumes
        avg_vol_5d = float(daily['Volume'].iloc[-6:-1].mean())  # avg last 5 days (excluding today)
        avg_vol_10d = float(daily['Volume'].iloc[-11:-1].mean()) # avg last 10 days
        yesterday_vol = float(daily['Volume'].iloc[-2]) if len(daily) >=2 else avg_vol_5d
        today_daily_vol = float(daily['Volume'].iloc[-1])  # today's total so far
        
        # Volume surge vs previous days - YOUR CORE ASK
        vol_vs_5d_avg = today_daily_vol / (avg_vol_5d + 1)
        vol_vs_yesterday = today_daily_vol / (yesterday_vol + 1)
        vol_vs_10d_avg = today_daily_vol / (avg_vol_10d + 1)
        
        # Intraday volume momentum (is volume increasing now?)
        vol_last_hour = float(intraday['Volume'].iloc[-4:].sum())
        vol_prev_hour = float(intraday['Volume'].iloc[-8:-4].sum())
        intraday_vol_accel = vol_last_hour / (vol_prev_hour + 1)
        
        # --- PRICE MOMENTUM vs Previous Days ---
        prev_close = float(daily['Close'].iloc[-2])
        prev_high = float(daily['High'].iloc[-2])
        five_day_high = float(daily['High'].iloc[-6:-1].max())
        twenty_day_high = float(daily['High'].iloc[-11:-1].max())
        
        price_vs_prev_close = (ltp / prev_close - 1) * 100
        is_breaking_prev_high = ltp > prev_high
        is_breaking_5d_high = ltp > five_day_high
        is_near_20d_high = ltp >= twenty_day_high * 0.98
        
        # Consecutive green days momentum
        daily_returns = daily['Close'].pct_change().iloc[-4:].tolist()  # last 3 days
        green_days = sum(1 for r in daily_returns if r > 0)
        
        # --- VWAP & ORB (intraday structure) ---
        vwap = float((intraday['Close'] * intraday['Volume']).sum() / (intraday['Volume'].sum() + 1))
        today_intraday = intraday[intraday.index.date == intraday.index[-1].date()]
        if len(today_intraday) < 2:
            today_intraday = intraday.iloc[-8:]
        or_high = float(today_intraday['High'].iloc[0:2].max())
        or_low = float(today_intraday['Low'].iloc[0:2].min())
        
        # --- YOUR FILTERS ---
        # Must have huge volume vs previous days
        if vol_vs_5d_avg < 1.5:  # at least 1.5x avg volume
            return None
        if vol_vs_yesterday < 1.2:  # more than yesterday
            return None
        if intraday_vol_accel < 1.1:  # volume accelerating now
            return None
        # Must have price momentum
        if price_vs_prev_close < 0.7:  # at least 0.7% up vs prev close
            return None
        if not is_breaking_prev_high:  # breaking yesterday high = momentum
            return None
        if ltp < vwap:  # must be above VWAP
            return None
        if ltp < or_high:  # must break opening range
            return None
        
        # --- SCORING ---
        score = 50  # base
        
        # Volume scoring (huge weight as you asked)
        if vol_vs_5d_avg > 3.0: score += 20
        elif vol_vs_5d_avg > 2.0: score += 15
        else: score += 8
        
        if vol_vs_yesterday > 2.0: score += 10
        elif vol_vs_yesterday > 1.5: score += 5
        
        if intraday_vol_accel > 1.8: score += 10
        
        # Price momentum scoring
        if price_vs_prev_close > 2.0: score += 15
        elif price_vs_prev_close > 1.2: score += 10
        else: score += 5
        
        if is_breaking_5d_high: score += 15
        elif is_breaking_prev_high: score += 8
        
        if is_near_20d_high: score += 5
        
        if green_days >= 3: score += 5  # 3 consecutive green days
        
        if score < 80: return None
        
        # High RR - tight SL, wide target
        sl = min(or_low, vwap * 0.997, prev_high * 0.998)
        risk = ltp - sl
        if risk <= 0 or (risk/ltp*100) > 1.2 or (risk/ltp*100) < 0.15:
            return None
        
        target = ltp + risk * 3.5  # 3.5R for momentum stocks
        
        return {
            "symbol": symbol,
            "used": used,
            "score": int(min(score, 99)),
            "setup": "5D High Break + Vol Surge" if is_breaking_5d_high else "Prev High Break + Vol Surge",
            "ltp": round(ltp,2),
            "prev_close": round(prev_close,2),
            "price_change_vs_prev": round(price_vs_prev_close,2),
            "vol_today": int(today_daily_vol),
            "vol_vs_5d_avg": round(vol_vs_5d_avg,2),
            "vol_vs_yesterday": round(vol_vs_yesterday,2),
            "vol_accel": round(intraday_vol_accel,2),
            "is_5d_high": is_breaking_5d_high,
            "green_days": green_days,
            "vwap_dist": round((ltp-vwap)/vwap*100,2),
            "entry": round(ltp,2),
            "sl": round(sl,2),
            "target": round(target,2),
            "risk_pct": round(risk/ltp*100,2),
            "reward_pct": round((target-ltp)/ltp*100,2),
            "rr": 3.5
        }
    except Exception as e:
        # print(f"{symbol} error {e}")
        return None

def scan_momentum_volume(universe, max_workers=12):
    results = []
    no_data = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {ex.submit(momentum_volume_score, s): s for s in universe}
        for f in as_completed(fut):
            try:
                res = f.result()
                if res: results.append(res)
            except Exception as e:
                no_data.append(str(e))
    # Sort by your priority: Volume surge + Price momentum
    return sorted(results, key=lambda x: (x['vol_vs_5d_avg'] * 2 + x['price_change_vs_prev'] + x['vol_accel']), reverse=True)[:5]
