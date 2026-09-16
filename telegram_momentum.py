import os, requests
BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
CHAT_ID = os.getenv("CHAT_ID","").strip()

print(f"DEBUG BOT_TOKEN exists: {bool(BOT_TOKEN)} len {len(BOT_TOKEN)}")
print(f"DEBUG CHAT_ID: {CHAT_ID}")

def push_momentum(stocks, is_test=False):
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: Missing BOT_TOKEN or CHAT_ID secrets in GitHub")
        return
    
    if not stocks:
        print("No live momentum stocks (market closed at night) - SENDING TEST ALERT to verify channel")
        # TEST DATA - proves repo + Telegram works
        stocks = [{
            "symbol": "RELIANCE",
            "score": 94,
            "setup": "TEST - 5D High Break + Vol Surge (Market Closed, Testing)",
            "ltp": 2845.5,
            "prev_close": 2805.0,
            "price_change_vs_prev": 1.44,
            "vol_today": 12500000,
            "vol_vs_5d_avg": 2.8,
            "vol_vs_yesterday": 2.1,
            "vol_accel": 1.9,
            "is_5d_high": True,
            "green_days": 3,
            "vwap_dist": 0.85,
            "entry": 2845.5,
            "sl": 2828.0,
            "target": 2906.0,
            "risk_pct": 0.61,
            "reward_pct": 2.13,
            "rr": 3.5
        }]
        is_test = True
    
    for i,s in enumerate(stocks,1):
        tag = "✅ TEST - Your New Repo Works!" if is_test else f"SURESHOT #{i}"
        msg = f"""🚀 {tag} - {s['symbol']} (Score {s['score']}/99) 🔥

Setup: {s['setup']}
Price: {s['ltp']} (Prev: {s['prev_close']} +{s['price_change_vs_prev']}%)
Volume TODAY: {s['vol_today']:,} vs 5D Avg: {s['vol_vs_5d_avg']}x | vs Yesterday: {s['vol_vs_yesterday']}x
Vol Accel: {s['vol_accel']}x | Green Days: {s['green_days']}/3 | 5D High Break: {'YES' if s['is_5d_high'] else 'NO'}

Entry: {s['entry']} | SL: {s['sl']} (-{s['risk_pct']}%) | TGT: {s['target']} (+{s['reward_pct']}% = {s['rr']}R)
VWAP: +{s['vwap_dist']}% | Momentum CONFIRMED

Why it will rise: Huge volume vs last 5 days + Breaking prev high + Vol accelerating
{'⚠️ THIS IS TEST ALERT - Live market at 09:35 will show real volume data' if is_test else ''}
"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
        print(f"Pushed {s['symbol']}: {r.status_code} - {r.text[:200]}")
        if r.status_code == 200:
            print("SUCCESS - Check Telegram Channel!")
        else:
            if "chat not found" in r.text:
                print("CHAT_ID wrong - add bot as admin and use -100... ID")
            if "Unauthorized" in r.text:
                print("BOT_TOKEN wrong")

if _name_ == "_main_":
    from nifty200_list import NIFTY_200
    try:
        from scanner_momentum_volume import scan_momentum_volume
        stocks = scan_momentum_volume(NIFTY_200[:40])  # Test with 40 for speed
        print(f"Found {len(stocks)} live momentum stocks")
    except Exception as e:
        print(f"Scanner error (expected at night): {e}")
        stocks = []
    push_momentum(stocks)
