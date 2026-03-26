import pandas as pd
import numpy as np
import json
import io

def load_data_from_logs():
    # Load prices from one log (they are identical)
    d1 = json.load(open('results/round0/23792.log'))
    df_p = pd.read_csv(io.StringIO(d1['activitiesLog']), sep=';')
    # Make sure we use Day -1 (or just use day column)
    
    # Load union of trades
    all_trades = []
    for fp in ['results/round0/23792.log', 'results/round0/23878.log', 'results/round0/23904.log', 'results/round0/23938.log']:
        d = json.load(open(fp))
        trades = d.get('tradeHistory', [])
        for t in trades:
            all_trades.append({
                'day': df_p['day'].iloc[0], # assuming same day
                'timestamp': t['timestamp'],
                'symbol': t['symbol'],
                'price': t['price'],
                'quantity': t['quantity']
            })
            
    df_t = pd.DataFrame(all_trades)
    # Take max volume for each timestamp/price combo to deduplicate
    df_t = df_t.groupby(['day', 'timestamp', 'symbol', 'price'])['quantity'].max().reset_index()
    
    return df_p, df_t

def simulate_tomatoes_exact(sma_window, margin, df_p, df_t):
    p = df_p[df_p['product'] == 'TOMATOES'].copy()
    t = df_t[df_t['symbol'] == 'TOMATOES'].copy()
    
    t_grouped = t.groupby(['day', 'timestamp']).agg(
        min_trade_price=('price', 'min'),
        max_trade_price=('price', 'max'),
        total_trade_vol=('quantity', 'sum') 
    ).reset_index()
    
    df = pd.merge(p, t_grouped, on=['day', 'timestamp'], how='left')
    df.sort_values(by=['day', 'timestamp'], inplace=True)
    
    # Calculate SMA and margins
    df['mid'] = (df['bid_price_1'] + df['ask_price_1']) / 2.0
    df['sma'] = df['mid'].rolling(sma_window).mean()
    df['our_bid'] = np.floor(df['sma'] - margin)
    df['our_ask'] = np.ceil(df['sma'] + margin)
    
    df['our_bid'] = np.minimum(df['our_bid'], df['bid_price_1'] + 1)
    df['our_ask'] = np.maximum(df['our_ask'], df['ask_price_1'] - 1)
    
    our_bids = df['our_bid'].values
    our_asks = df['our_ask'].values
    mid_prices = df['mid'].values
    
    next_min_trade = df['min_trade_price'].shift(-1).values
    next_max_trade = df['max_trade_price'].shift(-1).values
    next_ask = df['ask_price_1'].shift(-1).values
    next_bid = df['bid_price_1'].shift(-1).values
    next_trade_vol = df['total_trade_vol'].shift(-1).fillna(0).values
    
    pos = 0
    cash = 0
    limit = 80
    
    for i in range(len(df)-1):
        if np.isnan(our_bids[i]):
            continue
            
        b = our_bids[i]
        a = our_asks[i]
        
        bid_filled = False
        ask_filled = False
        
        # Did the limit cross us in the next tick?
        if next_ask[i] <= b:
            bid_filled = True
        # Or did a trade happen that hit our bid?
        elif not np.isnan(next_min_trade[i]) and next_min_trade[i] <= b:
            bid_filled = True
            
        if next_bid[i] >= a:
            ask_filled = True
        elif not np.isnan(next_max_trade[i]) and next_max_trade[i] >= a:
            ask_filled = True
            
        # Fill volumes
        if bid_filled and pos < limit:
            # We assume we get filled for up to 15 units
            qty = min(limit - pos, 15)
            pos += qty
            cash -= qty * b
            
        if ask_filled and pos > -limit:
            qty = min(pos + limit, 15)
            pos -= qty
            cash += qty * a
            
    pnl = cash + pos * mid_prices[-1]
    return pnl

if __name__ == "__main__":
    print("Loading data from logs...")
    df_p, df_t = load_data_from_logs()
    print("Loaded data. Running accurate gridsearch for TOMATOES on actual logged dataset...")
    
    best_pnl = -float('inf')
    best_sma = None
    best_margin = None

    for sma in range(2, 50, 1):
        for m in range(0, 10):
            pnl = simulate_tomatoes_exact(sma, m, df_p, df_t)
            if pnl > best_pnl:
                best_pnl = pnl
                best_sma = sma
                best_margin = m

    print(f"TOMATOES LOG-PRECISE - Best SMA: {best_sma}, Best Margin: {best_margin}, PNL: {best_pnl}")
    
    print("\nLandscape around optimum:")
    for sm in [best_sma-2, best_sma-1, best_sma, best_sma+1, best_sma+2]:
        if sm <= 0: continue
        for mar in [best_margin-1, best_margin, best_margin+1]:
            if mar < 0: continue
            cur_pnl = simulate_tomatoes_exact(sm, mar, df_p, df_t)
            print(f"SMA: {sm}, Margin: {mar}, PNL: {cur_pnl}")
