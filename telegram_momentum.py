
import os, requests
BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
CHAT_ID = os.getenv("CHAT_ID","").strip()

def push_momentum(stocks):
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing secrets")
        return
    
    if not stocks:
        print("No momentum + volume surge stocks today - capital protection")
        # Send no-trade message only at 10am
        # requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": "No high volume momentum sureshots today. Volume vs 5D avg <1.5x. No trade."})
        return
    
    for i,s in enumerate(stocks,1):
        msg = f"""🚀 SURESHOT #{i} - {s['symbol']} (Score {s['score']}/99) 🔥

Setup: {s['setup']}
Price: {s['ltp']} (Prev: {s['prev_close']} +{s['price_change_vs_prev']}%)
Volume TODAY: {s['vol_today']:,} vs 5D Avg: {s['vol_vs_5d_avg']}x | vs Yesterday: {s['vol_vs_yesterday']}x
Vol Accel: {s['vol_accel']}x | Green Days: {s['green_days']}/3 | 5D High Break: {'YES' if s['is_5d_high'] else 'NO'}

Entry: {s['entry']} | SL: {s['sl']} (-{s['risk_pct']}%) | TGT: {s['target']} (+{s['reward_pct']}% = {s['rr']}R)
VWAP: +{s['vwap_dist']}% | Momentum CONFIRMED

Why it will rise: Huge volume vs last 5 days + Breaking prev high + Vol accelerating
"""
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        print(f"Pushed {s['symbol']}: {r.status_code}")

if __name__ == "__main__":
    from nifty200_list import NIFTY_200
    from scanner_momentum_volume import scan_momentum_volume
    stocks = scan_momentum_volume(NIFTY_200)
    print(f"Found {len(stocks)} momentum volume surge stocks")
    for s in stocks:
        print(s)
    push_momentum(stocks)
