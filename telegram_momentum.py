
import os, requests
BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
CHAT_ID = os.getenv("CHAT_ID","").strip()

def push_momentum(stocks, is_test=False):
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing secrets")
        return
    
    if not stocks:
        print("No stocks even after relaxed filter - market extremely dull")
        stocks = [{
            "symbol": "RELIANCE", "score": 88, "tier": "TEST",
            "setup": "TEST - Market Closed - Repo Works",
            "ltp": 2845.5, "prev_close": 2805.0, "price_change_vs_prev": 1.44,
            "vol_today": 12500000, "vol_vs_5d_avg": 2.8, "vol_vs_yesterday": 2.1,
            "vol_accel": 1.9, "is_5d_high": True, "vwap_dist": 0.85,
            "entry": 2845.5, "sl": 2828.0, "target": 2906.0, "risk_pct": 0.61, "reward_pct": 2.13, "rr": 3.5
        }]
        is_test = True
    
    for i,s in enumerate(stocks,1):
        tier_emoji = "🔥" if s.get('tier')=='TIER1-STRICT' else "⚡" if s.get('tier')=='TIER2-RELAXED' else "✅"
        tag = f"{tier_emoji} {s.get('tier','')} - {s['symbol']}" if not is_test else f"✅ TEST - {s['symbol']}"
        msg = f"""🚀 SURESHOT #{i} - {tag} (Score {s['score']}/99)

Setup: {s['setup']}
Price: {s['ltp']} (Prev: {s['prev_close']} +{s['price_change_vs_prev']}%)
Volume TODAY: {s['vol_today']:,} vs 5D Avg: {s['vol_vs_5d_avg']}x | vs Yesterday: {s['vol_vs_yesterday']}x
Vol Accel: {s['vol_accel']}x | 5D High: {'YES' if s['is_5d_high'] else 'NO'}

Entry: {s['entry']} | SL: {s['sl']} (-{s['risk_pct']}%) | TGT: {s['target']} (+{s['reward_pct']}% = {s['rr']}R)
VWAP: +{s['vwap_dist']}%

Tier: {s.get('tier','')} - {'High Quality - High Vol + Momentum' if s.get('tier')=='TIER1-STRICT' else 'Relaxed - Best available on dull day' if s.get('tier')=='TIER2-RELAXED' else 'Test'}
"""
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        print(f"Pushed {s['symbol']} {s.get('tier')}: {r.status_code}")

if __name__ == "__main__":
    from nifty200_list import NIFTY_200
    from scanner_momentum_volume import scan_momentum_volume
    stocks = scan_momentum_volume(NIFTY_200)
    print(f"Final alerts: {len(stocks)}")
    for s in stocks: print(s)
    push_momentum(stocks)
