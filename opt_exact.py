import pandas as pd
import numpy as np

def load_data():
    prices = []
    trades = []
    for day in [-2, -1]:
        p = pd.read_csv(f'TUTORIAL_ROUND_1/prices_round_0_day_{day}.csv', sep=';')
        t = pd.read_csv(f'TUTORIAL_ROUND_1/trades_round_0_day_{day}.csv', sep=';')
        t['day'] = day
        p['day'] = day
        
        prices.append(p)
        trades.append(t)
    df_p = pd.concat(prices)
    df_t = pd.concat(trades)
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
        
        # Did the limit crossed us in the next tick?
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
            # We assume we get filled for 15 units if it crosses.
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
    print("Loading data...")
    df_p, df_t = load_data()
    print("Loaded data. Running accurate gridsearch for TOMATOES...")
    
    best_pnl = -float('inf')
    best_sma = None
    best_margin = None

    for sma in range(5, 40, 1):
        for m in range(0, 5):
            pnl = simulate_tomatoes_exact(sma, m, df_p, df_t)
            if pnl > best_pnl:
                best_pnl = pnl
                best_sma = sma
                best_margin = m

    print(f"TOMATOES PRECISE - Best SMA: {best_sma}, Best Margin: {best_margin}, PNL: {best_pnl}")
    
    # Also evaluate combinations of parameters just to see the exact landscape
    print("\nLandscape around optimum:")
    for sm in [best_sma-1, best_sma, best_sma+1]:
        if sm <= 0: continue
        for mar in [best_margin-1, best_margin, best_margin+1]:
            if mar < 0: continue
            cur_pnl = simulate_tomatoes_exact(sm, mar, df_p, df_t)
            print(f"SMA: {sm}, Margin: {mar}, PNL: {cur_pnl}")

