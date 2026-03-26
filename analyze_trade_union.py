import json, pandas as pd

all_trades = []
for fp in ['results/round0/23792.log', 'results/round0/23878.log', 'results/round0/23904.log']:
    d = json.load(open(fp))
    trades = d.get('tradeHistory', [])
    for t in trades:
        if t['symbol'] == 'TOMATOES':
            all_trades.append({
                'timestamp': t['timestamp'],
                'price': t['price'],
                'quantity': t['quantity']
            })

df = pd.DataFrame(all_trades)
# Take max quantity seen at that timestamp/price across the 3 runs
df_grouped = df.groupby(['timestamp', 'price'])['quantity'].max().reset_index()
print(f"Total reconstructed unique trade price levels: {len(df_grouped)}")
print(f"Total reconstructed volume: {df_grouped['quantity'].sum()}")
