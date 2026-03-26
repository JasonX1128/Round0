import json
from collections import defaultdict

logs = ['results/round0/23792.log', 'results/round0/23878.log', 'results/round0/23904.log']

tick_counts = defaultdict(int)
all_trades = defaultdict(list)

for i, fp in enumerate(logs):
    d = json.load(open(fp))
    for t in d.get('tradeHistory', []):
        if t['symbol'] == 'TOMATOES':
            tick_counts[t['timestamp']] += 1
            bot_action = "BOT BUY " if t['seller'] == 'SUBMISSION' else ("BOT SELL" if t['buyer'] == 'SUBMISSION' else "BOT TRDE")
            all_trades[t['timestamp']].append(f"Log{i}: {bot_action} @ {t['price']} x {t['quantity']}")

# Print a few where tick_counts > 2 and from different logs
for tick, trades in sorted(all_trades.items()):
    logs_involved = set([tr.split(':')[0] for tr in trades])
    if len(logs_involved) > 1:
        print(f"Tick {tick}:")
        for tr in trades: print("  " + tr)
