
import os, requests
BOT_TOKEN=os.getenv("BOT_TOKEN","").strip()
CHAT_ID=os.getenv("CHAT_ID","").strip()

def push_momentum(stocks, is_test=False):
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing secrets"); return
    if not stocks:
        print("Extremely dull - sending no-trade message")
        msg="⚠️ No momentum sureshots even in TIER2 today. Market extremely dull. No trade recommended. Capital protection."
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        return
    for i,s in enumerate(stocks,1):
        emoji="🔥" if s['tier']=='TIER1-STRICT' else "⚡"
        bb = f"BB {'BREAKOUT' if s['bb_breakout'] else 'Inside'} Upper {s['bb_upper']}"
        if s.get('bb_squeeze'): bb+=" + SQUEEZE=Explosive"
        pivot = f"{'Above R1' if s['above_r1'] else 'Above Pivot'} R1:{s['r1']}"
        msg=f"""🚀 SURESHOT #{i} - {emoji} {s['tier']} - {s['symbol']} (Score {s['score']}/99)

Setup: {s['setup']}
Price: {s['ltp']} (Prev: {s['prev_close']} +{s['price_change_vs_prev']}%)
Volume TODAY: {s['vol_today']:,} vs 5D {s['vol_vs_5d_avg']}x | vs Yest {s['vol_vs_yesterday']}x | Accel {s['vol_accel']}x

📊 CHART INDICATORS:
• {bb}
• PSAR {s['psar_trend']} | {pivot}
• RSI {s['rsi']} | EMA20 {s['ema20']} | VWAP +{s['vwap_dist']}%

Entry: {s['entry']} | SL: {s['sl']} (-{s['risk_pct']}%) | TGT: {s['target']} (+{s['reward_pct']}% = {s['rr']}R)

Why rise: {', '.join(s['indicators'][:5])}
"""
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        print(f"Pushed {s['symbol']} {s['tier']}: {r.status_code}")

if __name__=="__main__":
    from nifty200_list import NIFTY_200
    from scanner_momentum_volume import scan_momentum_volume
    stocks=scan_momentum_volume(NIFTY_200)
    print(f"Final alerts: {len(stocks)}")
    for s in stocks: print(s['symbol'], s['tier'], s['score'], s['indicators'])
    push_momentum(stocks)
