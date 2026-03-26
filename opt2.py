import pandas as pd
import numpy as np

df_t = pd.read_csv('outputs/TOMATOES/prices_processed.csv')
df_e = pd.read_csv('outputs/EMERALDS/prices_processed.csv')

def simulate_tomatoes(sma_window, margin):
    data = df_t.copy()
    data['sma'] = data['mid'].rolling(sma_window).mean()
    data['our_bid'] = np.floor(data['sma'] - margin)
    data['our_ask'] = np.ceil(data['sma'] + margin)
    
    data['best_bid'] = data['bid_price_1']
    data['best_ask'] = data['ask_price_1']
    
    data['our_bid'] = np.minimum(data['our_bid'], data['best_bid'] + 1)
    data['our_ask'] = np.maximum(data['our_ask'], data['best_ask'] - 1)
    
    next_ask = data['best_ask'].shift(-1).values
    next_bid = data['best_bid'].shift(-1).values
    our_bids = data['our_bid'].values
    our_asks = data['our_ask'].values
    mid = data['mid'].values
    
    # We get filled if the price moves aggressively through our resting order
    bid_eaten = (next_bid < our_bids) | (next_ask <= our_bids)
    ask_eaten = (next_ask > our_asks) | (next_bid >= our_asks)
    
    pos = 0
    cash = 0
    limit = 80
    
    for i in range(len(data)-1):
        if np.isnan(our_bids[i]):
            continue
            
        b = our_bids[i]
        a = our_asks[i]
        
        if bid_eaten[i] and pos < limit:
            qty = min(limit - pos, 15) 
            pos += qty
            cash -= qty * b
            
        if ask_eaten[i] and pos > -limit:
            qty = min(pos + limit, 15)
            pos -= qty
            cash += qty * a
            
    pnl = cash + pos * mid[-1]
    return pnl

best_pnl = -float('inf')
best_sma = None
best_margin = None

print("Optimizing TOMATOES...")
for sma in range(10, 100, 5):
    for m in range(0, 4):
        pnl = simulate_tomatoes(sma, m)
        if pnl > best_pnl:
            best_pnl = pnl
            best_sma = sma
            best_margin = m

print(f"TOMATOES - Best SMA: {best_sma}, Best Margin: {best_margin}, PNL: {best_pnl}")

def simulate_emeralds(margin):
    data = df_e.copy()
    data['our_bid'] = 10000 - margin
    data['our_ask'] = 10000 + margin
    
    data['best_bid'] = data['bid_price_1']
    data['best_ask'] = data['ask_price_1']
    
    data['our_bid'] = np.minimum(data['our_bid'], data['best_bid'] + 1)
    data['our_ask'] = np.maximum(data['our_ask'], data['best_ask'] - 1)
    
    next_ask = data['best_ask'].shift(-1).values
    next_bid = data['best_bid'].shift(-1).values
    our_bids = data['our_bid'].values
    our_asks = data['our_ask'].values
    mid = data['mid'].values
    
    bid_eaten = (next_bid < our_bids) | (next_ask <= our_bids)
    ask_eaten = (next_ask > our_asks) | (next_bid >= our_asks)
    
    pos = 0
    cash = 0
    limit = 80
    
    for i in range(len(data)-1):
        b = our_bids[i]
        a = our_asks[i]
        
        if bid_eaten[i] and pos < limit:
            qty = min(limit - pos, 15)
            pos += qty
            cash -= qty * b
            
        if ask_eaten[i] and pos > -limit:
            qty = min(pos + limit, 15)
            pos -= qty
            cash += qty * a
            
    pnl = cash + pos * 10000
    return pnl

print("Optimizing EMERALDS...")
best_e_margin = None
best_e_pnl = -float('inf')
for m in range(1, 10):
    pnl = simulate_emeralds(m)
    if pnl > best_e_pnl:
        best_e_pnl = pnl
        best_e_margin = m
        
print(f"EMERALDS - Best Margin: {best_e_margin}, PNL: {best_e_pnl}")
