import json

logs = ['results/round0/23792.log', 'results/round0/23878.log', 'results/round0/23904.log']

tick = 1900
for i, fp in enumerate(logs):
    d = json.load(open(fp))
    trades = [t for t in d.get('tradeHistory', []) if t['timestamp'] == tick and t['symbol'] == 'TOMATOES']
    print(f"Log {i+1}:")
    for t in trades:
        bot_action = "BOT BUY " if t['seller'] == 'SUBMISSION' else ("BOT SELL" if t['buyer'] == 'SUBMISSION' else "BOT TRDE")
        print(f"  {bot_action} - Price: {t['price']}, Qty: {t['quantity']}")
