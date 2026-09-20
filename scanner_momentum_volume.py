
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

SYMBOL_FIXES = {
    "M&M": "M&M.NS", "MCDOWELL-N": "MCDOWELL-N.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BANKBEES": "BANKBEES.NS", "MID150BEES": "MID150BEES.NS", "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS", "GOLDBEES": "GOLDBEES.NS", "SILVERBEES": "SILVERBEES.NS",
    "ITBEES": "ITBEES.NS", "PSUBNKBEES": "PSUBNKBEES.NS", "PHARMABEES": "PHARMABEES.NS",
    "MOM30IETF": "MOM30IETF.NS", "MID150MOM50": "MID150MOM50.NS", "MON100": "MON100.NS",
    "MAFANG": "MAFANG.NS", "ALPHAIETF": "ALPHAIETF.NS", "CPSEBEES": "CPSEBEES.NS",
}

def bollinger(close, period=20, std=2):
    if len(close) < period: return None, None, None, None, 50
    sma = close.rolling(period).mean().iloc[-1]
    sd = close.rolling(period).std().iloc[-1]
    upper = sma + std*sd
    lower = sma - std*sd
    bw = (upper-lower)/sma*100 if sma else 0
    pct = (close.iloc[-1]-lower)/(upper-lower)*100 if upper!=lower else 50
    return sma, upper, lower, bw, pct

def pivot_levels(h, l, c):
    if len(c)<2: return None,None,None,None
    ph, pl, pc = h.iloc[-2], l.iloc[-2], c.iloc[-2]
    piv = (ph+pl+pc)/3
    r1 = 2*piv - pl
    r2 = piv + (ph-pl)
    s1 = 2*piv - ph
    return piv, r1, r2, s1

def rsi_calc(close, period=14):
    if len(close)<period+1: return 50
    d = close.diff()
    g = d.where(d>0,0).rolling(period).mean()
    ls = (-d.where(d<0,0)).rolling(period).mean()
    rs = g/ls
    rsi = 100 - (100/(1+rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

def fetch(symbol):
    ticker = SYMBOL_FIXES.get(symbol, f"{symbol}.NS")
    try:
        t = yf.Ticker(ticker)
        intra = t.history(period="5d", interval="15m", timeout=20)
        daily = t.history(period="30d", interval="1d", timeout=20)
        if intra.empty or daily.empty or len(daily)<21:
            return None,None,ticker
        return intra,daily,ticker
    except:
        return None,None,ticker

def score(symbol, strict=True):
    intra,daily,ticker = fetch(symbol)
    if intra is None: return None
    try:
        ltp = float(intra['Close'].iloc[-1])
        if ltp<15: return None
        avg5 = float(daily['Volume'].iloc[-6:-1].mean())
        yvol = float(daily['Volume'].iloc[-2])
        tvol = float(daily['Volume'].iloc[-1])
        vs5 = tvol/(avg5+1)
        vsY = tvol/(yvol+1)
        last_h = float(intra['Volume'].iloc[-4:].sum())
        prev_h = float(intra['Volume'].iloc[-8:-4].sum())
        accel = last_h/(prev_h+1) if prev_h>0 else 1

        pc = float(daily['Close'].iloc[-2])
        ph = float(daily['High'].iloc[-2])
        fdh = float(daily['High'].iloc[-6:-1].max())
        chg = (ltp/pc-1)*100
        brkPrev = ltp>ph
        brk5 = ltp>fdh

        vwap = float((intra['Close']*intra['Volume']).sum()/(intra['Volume'].sum()+1))
        today = intra[intra.index.date==intra.index[-1].date()]
        if len(today)<2: today=intra.iloc[-8:]
        orh = float(today['High'].iloc[0:2].max())
        orl = float(today['Low'].iloc[0:2].min())

        # Chart indicators
        bb_sma, bb_up, bb_low, bb_bw, bb_pct = bollinger(daily['Close'])
        bb_break = ltp>bb_up if bb_up else False
        bb_squeeze = bb_bw<10 if bb_bw else False

        piv, r1, r2, s1 = pivot_levels(daily['High'], daily['Low'], daily['Close'])
        above_r1 = ltp>r1 if r1 else False
        above_piv = ltp>piv if piv else True

        rsi = rsi_calc(daily['Close'])
        ema20 = float(daily['Close'].ewm(span=20).mean().iloc[-1])
        ema50 = float(daily['Close'].ewm(span=50).mean().iloc[-1])
        bull = ema20>ema50 and ltp>ema20 if ema20 and ema50 else True
        psar_up = ltp>ema20  # simplified PSAR proxy

        # Filters - TIER1 strict, TIER2 loose to guarantee 1-2 alerts
        if strict:
            if vs5<0.9: return None
            if chg<0.35: return None
            if not brkPrev: return None
            if ltp<vwap*0.997: return None
            if ltp<orh*0.997: return None
            if rsi>88 or rsi<32: return None
            if not psar_up: return None
        else:
            if chg<0.08: return None
            if ltp<vwap*0.993: return None
            if vs5<0.55: return None
            if rsi<28: return None

        score=35
        inds=[]
        if vs5>3: score+=18; inds.append(f"Vol {vs5:.1f}x")
        elif vs5>2: score+=12
        elif vs5>1: score+=6
        else: score+=2
        if vsY>2: score+=7
        if accel>1.5: score+=5; inds.append("Vol Accel")
        if chg>2: score+=14
        elif chg>1: score+=9
        elif chg>0.5: score+=4
        if brk5: score+=11; inds.append("5D High")
        elif brkPrev: score+=5; inds.append("Prev High")
        if bb_break: score+=11; inds.append("BB Breakout")
        elif bb_pct>80: score+=5; inds.append(f"BB {bb_pct:.0f}%")
        if bb_squeeze: score+=7; inds.append("BB Squeeze")
        if above_r1: score+=9; inds.append("Above R1")
        elif above_piv: score+=3
        if 55<=rsi<=76: score+=7; inds.append(f"RSI {rsi:.0f}")
        if bull: score+=8; inds.append("EMA 20>50 Bull")
        elif ltp>ema20: score+=3
        if psar_up: score+=6; inds.append("PSAR Bull")

        bonus=12 if strict else 0
        sl = min(orl, vwap*0.996, ph*0.997, s1 if s1 else orl) if strict else min(orl, vwap*0.994)
        risk = ltp-sl
        if risk<=0: return None
        rpct = risk/ltp*100
        if strict:
            if rpct>1.4 or rpct<0.09: return None
        else:
            if rpct>2.3 or rpct<0.06: return None
        tgt = ltp + risk*(3.5 if strict else 2.8)
        final = score+bonus
        if final < (70 if strict else 40): return None

        return {
            "symbol": symbol, "score": int(min(final,99)), "tier": "TIER1-STRICT" if strict else "TIER2-RELAXED",
            "setup": " + ".join(inds[:4]) if inds else "Momentum + Vol",
            "ltp": round(ltp,2), "prev_close": round(pc,2), "price_change_vs_prev": round(chg,2),
            "vol_today": int(tvol), "vol_vs_5d_avg": round(vs5,2), "vol_vs_yesterday": round(vsY,2),
            "vol_accel": round(accel,2), "is_5d_high": brk5, "vwap_dist": round((ltp-vwap)/vwap*100,2),
            "bb_upper": round(bb_up,2) if bb_up else 0, "bb_breakout": bb_break, "bb_squeeze": bb_squeeze,
            "psar_trend": "UP" if psar_up else "DOWN", "pivot": round(piv,2) if piv else 0,
            "r1": round(r1,2) if r1 else 0, "above_r1": above_r1, "rsi": round(rsi,1),
            "ema20": round(ema20,2), "above_ema20": ltp>ema20,
            "entry": round(ltp,2), "sl": round(sl,2), "target": round(tgt,2),
            "risk_pct": round(rpct,2), "reward_pct": round((tgt-ltp)/ltp*100,2), "rr": 3.5 if strict else 2.8,
            "indicators": inds
        }
    except:
        return None

def scan_momentum_volume(universe, max_workers=12):
    t1=[]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut={ex.submit(score,s,True):s for s in universe}
        for f in fut:
            try:
                r=f.result()
                if r: t1.append(r)
            except: pass
    print(f"TIER1 Strict found: {len(t1)}")
    if len(t1)>=1:
        return sorted(t1, key=lambda x: (x['score']*2 + x['vol_vs_5d_avg'] + (10 if x['bb_breakout'] else 0)), reverse=True)[:5]
    print("No TIER1, fallback TIER2")
    t2=[]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut={ex.submit(score,s,False):s for s in universe}
        for f in fut:
            try:
                r=f.result()
                if r: t2.append(r)
            except: pass
    print(f"TIER2 found: {len(t2)}")
    return sorted(t2, key=lambda x: (x['score']+x['vol_vs_5d_avg']), reverse=True)[:5] if t2 else []
