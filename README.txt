
SURESHOT SCANNER - FINAL VERSION (Momentum + Huge Volume vs Prev Days)

FILES:
- nifty200_list.py - 215 symbols (200 Nifty + 15 liquid ETFs)
- scanner_momentum_volume.py - MAIN SCANNER - checks volume vs 5d avg, vs yesterday, price breaking prev highs, 3.5R
- telegram_momentum.py - pushes momentum volume surge alerts
- scanner_robust.py - fallback robust fetcher
- scanner_high_rr.py - high RR 3R version
- hosted_main.py - scheduler (for local/PythonAnywhere)
- telegram_pro.py - original telegram

GITHUB SETUP:
.github/workflows/scan.yml should run:
  python telegram_momentum.py

It will auto-scan at 09:35, 10:05, 11:00, 13:30 IST and push to Telegram.

Filters:
- Vol today >1.5x avg 5d and >1.2x yesterday
- Vol accelerating last hour
- Price > yesterday high + > VWAP + > OR High
- Breaking 5d high bonus
- Risk 0.15-1.2%, Target 3.5R

ETFs added: BANKBEES, NIFTYBEES, MID150BEES, JUNIORBEES, ITBEES, PSUBNKBEES, PHARMABEES, MOM30IETF, MID150MOM50, MON100, MAFANG, SILVERBEES, GOLDBEES, ALPHAIETF, CPSEBEES
