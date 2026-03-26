import pandas as pd
import numpy as np
import json
import io
from collections import defaultdict

def load_empirical_data():
    logs = ['results/round0/23792.log', 'results/round0/23878.log', 'results/round0/23904.log']
    
    # Load prices
    d0 = json.load(open(logs[0]))
    df = pd.read_csv(io.StringIO(d0['activitiesLog']), sep=';')
    df = df[df['product'] == 'TOMATOES'].copy()
    df.sort_values('timestamp', inplace=True)
    
    bot_buys_temp = defaultdict(lambda: defaultdict(list))
    bot_sells_temp = defaultdict(lambda: defaultdict(list))
    
    for fp in logs:
        d = json.load(open(fp))
        
        run_buys = defaultdict(lambda: defaultdict(int))
        run_sells = defaultdict(lambda: defaultdict(int))
        
        for t in d.get('tradeHistory', []):
            if t['symbol'] != 'TOMATOES':
                continue
            ts = t['timestamp']
            price = t['price']
            qty = t['quantity']
            
            # BOT BUY: bot is buyer
            if t['seller'] == 'SUBMISSION' or t['seller'] == '':
                run_buys[ts][price] += qty
            
            # BOT SELL: bot is seller
            if t['buyer'] == 'SUBMISSION' or t['buyer'] == '':
                run_sells[ts][price] += qty
                
        # Update cross-log records
        for ts, p_dict in run_buys.items():
            for p, q in p_dict.items():
                bot_buys_temp[ts][p].append(q)
                
        for ts, p_dict in run_sells.items():
            for p, q in p_dict.items():
                bot_sells_temp[ts][p].append(q)
                
    # Use the max observed quantity to represent the willingness to trade
    bot_buys = {}
    bot_sells = {}
    for ts, p_dict in bot_buys_temp.items():
        bot_buys[ts] = [(p, max(qs)) for p, qs in p_dict.items()]
    for ts, p_dict in bot_sells_temp.items():
        bot_sells[ts] = [(p, max(qs)) for p, qs in p_dict.items()]
        
    return df, bot_buys, bot_sells

def simulate_tomatoes_empirical(sma_window, margin, df, bot_buys, bot_sells):
    prices = df.copy()
    
    prices['mid'] = (prices['bid_price_1'] + prices['ask_price_1']) / 2.0
    prices['sma'] = prices['mid'].rolling(sma_window).mean()
    prices['our_bid'] = np.floor(prices['sma'] - margin)
    prices['our_ask'] = np.ceil(prices['sma'] + margin)
    
    prices['our_bid'] = np.minimum(prices['our_bid'], prices['bid_price_1'] + 1)
    prices['our_ask'] = np.maximum(prices['our_ask'], prices['ask_price_1'] - 1)
    
    our_bids = prices['our_bid'].values
    our_asks = prices['our_ask'].values
    mid_prices = prices['mid'].values
    
    next_ask = prices['ask_price_1'].shift(-1).values
    next_bid = prices['bid_price_1'].shift(-1).values
    
    timestamps = prices['timestamp'].values
    next_timestamps = np.append(timestamps[1:], [0])
    
    pos = 0
    cash = 0
    limit = 80
    
    for i in range(len(prices)-1):
        if np.isnan(our_bids[i]):
            continue
            
        b = our_bids[i]
        a = our_asks[i]
        
        nts = next_timestamps[i]
        
        bid_qty = 0
        ask_qty = 0
        
        if next_ask[i] <= b:
            bid_qty = 15
            
        if next_bid[i] >= a:
            ask_qty = 15
            
        b_sells = bot_sells.get(nts, [])
        for p, q in b_sells:
            # Bot sells at P means we need to bid at least P to get filled
            if b >= p:
                bid_qty = max(bid_qty, q)
                
        b_buys = bot_buys.get(nts, [])
        for p, q in b_buys:
            # Bot buys at P means we need to ask at most P to get filled
            if a <= p:
                ask_qty = max(ask_qty, q)

        if bid_qty > 0 and pos < limit:
            qty = min(limit - pos, bid_qty)
            pos += qty
            cash -= qty * b
            
        if ask_qty > 0 and pos > -limit:
            qty = min(pos + limit, ask_qty)
            pos -= qty
            cash += qty * a
            
    pnl = cash + pos * mid_prices[-1]
    return pnl

if __name__ == "__main__":
    df, bot_buys, bot_sells = load_empirical_data()
    best_pnl = -float('inf')
    best_sma = None
    best_margin = None

    for sma in range(2, 201, 1):
        if sma % 10 == 0:
            print(f"Searching SMA={sma}...", flush=True)
        for m in range(0, 20):
            pnl = simulate_tomatoes_empirical(sma, m, df, bot_buys, bot_sells)
            if pnl > best_pnl:
                best_pnl = pnl
                best_sma = sma
                best_margin = m

    print(f"TOMATOES EMPIRICAL LOG - Best SMA: {best_sma}, Best Margin: {best_margin}, PNL: {best_pnl}")
    
    print("\nLandscape around optimum:")
    for sm in [best_sma-2, best_sma-1, best_sma, best_sma+1, best_sma+2]:
        if sm <= 0: continue
        for mar in [best_margin-1, best_margin, best_margin+1]:
            if mar < 0: continue
            cur_pnl = simulate_tomatoes_empirical(sm, mar, df, bot_buys, bot_sells)
            print(f"SMA: {sm}, Margin: {mar}, PNL: {cur_pnl}")
