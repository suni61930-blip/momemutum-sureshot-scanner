
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

SYMBOL_FIXES = {
    "M&M": "M&M.NS", "MCDOWELL-N": "MCDOWELL-N.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BANKBEES": "BANKBEES.NS", "MID150BEES": "MID150BEES.NS", "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS", "GOLDBEES": "GOLDBEES.NS", "SILVERBEES": "SILVERBEES.NS",
    "ITBEES": "ITBEES.NS", "PSUBNKBEES": "PSUBNKBEES.NS", "PHARMABEES": "PHARMABEES.NS",
    "MOM30IETF": "MOM30IETF.NS", "MID150MOM50": "MID150MOM50.NS", "MON100": "MON100.NS",
    "MAFANG": "MAFANG.NS", "ALPHAIETF": "ALPHAIETF.NS", "CPSEBEES": "CPSEBEES.NS",
}

def fetch_multi_timeframe(symbol):
    ticker_str = SYMBOL_FIXES.get(symbol, f"{symbol}.NS")
    try:
        t = yf.Ticker(ticker_str)
        intraday = t.history(period="5d", interval="15m", timeout=15)
        daily = t.history(period="20d", interval="1d", timeout=15)
        if intraday.empty or daily.empty or len(daily) < 6:
            return None, None, ticker_str
        return intraday, daily, ticker_str
    except:
        return None, None, ticker_str

def score_symbol(symbol, strict=True):
    intraday, daily, used = fetch_multi_timeframe(symbol)
    if intraday is None or daily is None:
        return None
    
    try:
        ltp = float(intraday['Close'].iloc[-1])
        if ltp < 15: return None
        
        avg_vol_5d = float(daily['Volume'].iloc[-6:-1].mean())
        yesterday_vol = float(daily['Volume'].iloc[-2]) if len(daily)>=2 else avg_vol_5d
        today_daily_vol = float(daily['Volume'].iloc[-1])
        vol_vs_5d_avg = today_daily_vol / (avg_vol_5d + 1)
        vol_vs_yesterday = today_daily_vol / (yesterday_vol + 1)
        vol_last_hour = float(intraday['Volume'].iloc[-4:].sum())
        vol_prev_hour = float(intraday['Volume'].iloc[-8:-4].sum())
        intraday_vol_accel = vol_last_hour / (vol_prev_hour + 1) if vol_prev_hour>0 else 1
        
        prev_close = float(daily['Close'].iloc[-2])
        prev_high = float(daily['High'].iloc[-2])
        five_day_high = float(daily['High'].iloc[-6:-1].max())
        twenty_day_high = float(daily['High'].iloc[-11:-1].max())
        
        price_vs_prev_close = (ltp / prev_close - 1) * 100
        is_breaking_prev_high = ltp > prev_high
        is_breaking_5d_high = ltp > five_day_high
        is_near_20d_high = ltp >= twenty_day_high * 0.98
        
        vwap = float((intraday['Close'] * intraday['Volume']).sum() / (intraday['Volume'].sum() + 1))
        today_intraday = intraday[intraday.index.date == intraday.index[-1].date()]
        if len(today_intraday) < 2:
            today_intraday = intraday.iloc[-8:]
        or_high = float(today_intraday['High'].iloc[0:2].max())
        or_low = float(today_intraday['Low'].iloc[0:2].min())
        
        # === FILTERS ===
        if strict:
            # TIER 1 - STRICT (High quality)
            if vol_vs_5d_avg < 1.2: return None
            if vol_vs_yesterday < 1.0: return None
            if price_vs_prev_close < 0.5: return None
            if not is_breaking_prev_high: return None
            if ltp < vwap: return None
            if ltp < or_high: return None
            if intraday_vol_accel < 1.0: return None
        else:
            # TIER 2 - RELAXED (Guarantee 1-2 alerts even on dull day)
            # Only absolutely necessary filters
            if price_vs_prev_close < 0.15: return None  # at least slightly green
            if ltp < vwap * 0.998: return None  # allow small dip below VWAP
            if vol_vs_5d_avg < 0.7: return None  # at least 70% of avg
            if ltp < 15: return None
        
        score = 40
        # Volume
        if vol_vs_5d_avg > 3.0: score += 20
        elif vol_vs_5d_avg > 2.0: score += 15
        elif vol_vs_5d_avg > 1.2: score += 8
        else: score += 3
        
        if vol_vs_yesterday > 2.0: score += 10
        elif vol_vs_yesterday > 1.3: score += 5
        
        if intraday_vol_accel > 1.5: score += 8
        
        # Price momentum
        if price_vs_prev_close > 2.0: score += 15
        elif price_vs_prev_close > 1.0: score += 10
        elif price_vs_prev_close > 0.5: score += 5
        else: score += 2
        
        if is_breaking_5d_high: score += 12
        elif is_breaking_prev_high: score += 6
        
        if is_near_20d_high: score += 4
        
        # Tier bonus
        tier_bonus = 10 if strict else 0
        
        sl = min(or_low, vwap * 0.997, prev_high * 0.998) if strict else min(or_low, vwap * 0.995)
        risk = ltp - sl
        if risk <=0: return None
        risk_pct = risk/ltp*100
        if strict:
            if risk_pct > 1.2 or risk_pct < 0.12: return None
        else:
            if risk_pct > 2.0 or risk_pct < 0.08: return None
        
        target = ltp + risk * (3.5 if strict else 2.8)
        
        # For relaxed, allow lower score
        min_score = 75 if strict else 45
        final_score = score + tier_bonus
        if final_score < min_score: return None
        
        return {
            "symbol": symbol,
            "used": used,
            "score": int(min(final_score, 99)),
            "tier": "TIER1-STRICT" if strict else "TIER2-RELAXED",
            "setup": "5D High Break + Vol Surge" if is_breaking_5d_high else "Prev High Break + Vol Surge" if is_breaking_prev_high else "Momentum + Vol",
            "ltp": round(ltp,2),
            "prev_close": round(prev_close,2),
            "price_change_vs_prev": round(price_vs_prev_close,2),
            "vol_today": int(today_daily_vol),
            "vol_vs_5d_avg": round(vol_vs_5d_avg,2),
            "vol_vs_yesterday": round(vol_vs_yesterday,2),
            "vol_accel": round(intraday_vol_accel,2),
            "is_5d_high": is_breaking_5d_high,
            "is_prev_high": is_breaking_prev_high,
            "vwap_dist": round((ltp-vwap)/vwap*100,2),
            "entry": round(ltp,2),
            "sl": round(sl,2),
            "target": round(target,2),
            "risk_pct": round(risk_pct,2),
            "reward_pct": round((target-ltp)/ltp*100,2),
            "rr": 3.5 if strict else 2.8
        }
    except Exception as e:
        return None

def scan_momentum_volume(universe, max_workers=12):
    """Guarantee 1-2 alerts: Try strict first, fallback to relaxed"""
    tier1 = []
    tier2 = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # First pass strict
        fut1 = {ex.submit(score_symbol, s, True): s for s in universe}
        for f in as_completed(fut1):
            res = f.result()
            if res: tier1.append(res)
    
    print(f"TIER1 Strict found: {len(tier1)}")
    
    if len(tier1) >= 1:
        # We have at least 1 high quality - return top 5 strict
        sorted_t1 = sorted(tier1, key=lambda x: (x['vol_vs_5d_avg']*2 + x['price_change_vs_prev'] + x['vol_accel']), reverse=True)
        return sorted_t1[:5]
    
    # No strict found - market dull, fallback to relaxed to guarantee 1-2 alerts
    print("No TIER1, falling back to TIER2 Relaxed to guarantee 1-2 alerts")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut2 = {ex.submit(score_symbol, s, False): s for s in universe}
        for f in as_completed(fut2):
            res = f.result()
            if res: tier2.append(res)
    
    print(f"TIER2 Relaxed found: {len(tier2)}")
    if tier2:
        sorted_t2 = sorted(tier2, key=lambda x: (x['score'] + x['vol_vs_5d_avg'] + x['price_change_vs_prev']), reverse=True)
        return sorted_t2[:5]
    
    return []
