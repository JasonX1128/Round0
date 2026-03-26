import json
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)
json_encoder = NpEncoder
import pandas as pd
import numpy as np
import os
import glob
from trader import Trader
from datamodel import TradingState, OrderDepth, Listing, Observation

def generate_log_from_historical(data_dir, output_log_path):
    """
    Simulates the exchange engine using historical data, running the Trader logic,
    and outputting a log file in exactly the same format as the live exchange.
    """
    price_cols = ['day', 'timestamp', 'product', 'bid_price_1', 'bid_volume_1', 'bid_price_2', 'bid_volume_2', 'bid_price_3', 'bid_volume_3', 'ask_price_1', 'ask_volume_1', 'ask_price_2', 'ask_volume_2', 'ask_price_3', 'ask_volume_3', 'mid_price', 'profit_and_loss']
    
    price_dfs = []
    
    # Load all available days of data and sort
    for file in glob.glob(os.path.join(data_dir, "prices_round_0_day_*.csv")):
        df = pd.read_csv(file, sep=';')
        price_dfs.append(df)
        
    if not price_dfs:
        print("No historical data found.")
        return
        
    prices = pd.concat(price_dfs, ignore_index=True)
    prices.sort_values(['day', 'timestamp'], inplace=True)
    
    trader = Trader()
    
    trader_data = ""
    # We maintain our own simulated states for the log
    positions = {"EMERALDS": 0, "TOMATOES": 0}
    cash = {"EMERALDS": 0.0, "TOMATOES": 0.0}
    pnl = {"EMERALDS": 0.0, "TOMATOES": 0.0}
    
    # Structures for output JSON
    activities_list = []
    trade_history = []
    
    # Replay by timestamp across all days sequentially
    grouped = prices.groupby(['day', 'timestamp'])
    
    for (day, ts), frame_df in grouped:
        order_depths = {}
        listings = {}
        mid_prices = {}
        
        # Build state
        for _, row in frame_df.iterrows():
            product = row['product']
            listings[product] = Listing(product, product, "XIRECS")
            depth = OrderDepth()
            
            mid_prices[product] = row['mid_price']
            
            # Map buy/sell orders. (Wait, buy_volume represents what we CAN buy or what the MARKET bids?)
            # The market bids (buy_orders in order depth)
            for i in range(1, 4):
                bid_p = row.get(f'bid_price_{i}')
                bid_v = row.get(f'bid_volume_{i}')
                if pd.notna(bid_p) and pd.notna(bid_v):
                    depth.buy_orders[int(bid_p)] = int(bid_v)
                    
                ask_p = row.get(f'ask_price_{i}')
                ask_v = row.get(f'ask_volume_{i}')
                if pd.notna(ask_p) and pd.notna(ask_v):
                    depth.sell_orders[int(ask_p)] = -int(ask_v) # convention is negative
                    
            order_depths[product] = depth
            
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings=listings,
            order_depths=order_depths,
            own_trades={},
            market_trades={},
            position=positions.copy(),
            observations=Observation({}, {})
        )
        
        # Execute strategy
        orders_dict, _, new_trader_data = trader.run(state)
        trader_data = new_trader_data
        
        # Simulate simple execution against this frame's orderbook
        for product, orders in orders_dict.items():
            depth = order_depths[product]
            for order in orders:
                if order.quantity > 0: # We buy
                    # We can buy from market sellers (sell_orders)
                    # For simplicity in offline sim, if we put an order >= best ask, we trade
                    best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else float('inf')
                    if order.price >= best_ask:
                        # Filled
                        exec_qty = min(order.quantity, -depth.sell_orders[best_ask])
                        positions[product] += exec_qty
                        cash[product] -= exec_qty * best_ask
                        trade_history.append({
                            "timestamp": ts,
                            "buyer": "SUBMISSION",
                            "seller": "",
                            "symbol": product,
                            "currency": "XIRECS",
                            "price": int(best_ask),
                            "quantity": int(exec_qty)
                        })
                elif order.quantity < 0: # We sell
                    best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else -float('inf')
                    if order.price <= best_bid:
                        # Filled
                        exec_qty = min(abs(order.quantity), depth.buy_orders[best_bid])
                        positions[product] -= exec_qty
                        cash[product] += exec_qty * best_bid
                        trade_history.append({
                            "timestamp": ts,
                            "buyer": "",
                            "seller": "SUBMISSION",
                            "symbol": product,
                            "currency": "XIRECS",
                            "price": int(best_bid),
                            "quantity": int(exec_qty)
                        })
        
        # Update PnL calculation and activities log
        for _, row in frame_df.iterrows():
            product = row['product']
            current_pnl = cash[product] + (positions[product] * mid_prices[product])
            
            pnl[product] = current_pnl
            
            # format matching the activitiesLog
            act_row = [
                str(day), str(ts), product,
                str(row['bid_price_1']) if pd.notna(row['bid_price_1']) else "",
                str(row['bid_volume_1']) if pd.notna(row['bid_volume_1']) else "",
                str(row['bid_price_2']) if pd.notna(row['bid_price_2']) else "",
                str(row['bid_volume_2']) if pd.notna(row['bid_volume_2']) else "",
                str(row['bid_price_3']) if pd.notna(row['bid_price_3']) else "",
                str(row['bid_volume_3']) if pd.notna(row['bid_volume_3']) else "",
                str(row['ask_price_1']) if pd.notna(row['ask_price_1']) else "",
                str(row['ask_volume_1']) if pd.notna(row['ask_volume_1']) else "",
                str(row['ask_price_2']) if pd.notna(row['ask_price_2']) else "",
                str(row['ask_volume_2']) if pd.notna(row['ask_volume_2']) else "",
                str(row['ask_price_3']) if pd.notna(row['ask_price_3']) else "",
                str(row['ask_volume_3']) if pd.notna(row['ask_volume_3']) else "",
                str(row['mid_price']),
                str(current_pnl)
            ]
            activities_list.append(";".join(act_row))
            
    # Compile the final log JSON
    activities_csv = "day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss\n" + "\n".join(activities_list)
    
    out_data = {
        "submissionId": "local-sim-1234",
        "activitiesLog": activities_csv,
        "logs": "",
        "tradeHistory": trade_history
    }
    
    os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
    with open(output_log_path, 'w') as f:
        json.dump(out_data, f, cls=json_encoder)
        
    print(f"Simulation complete. Log written to {output_log_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Simulate trader over historical price data to generate logs")
    parser.add_argument("--data", type=str, default="../../TUTORIAL_ROUND_1", help="Path to the historical data dir")
    parser.add_argument("--out", type=str, default="../../outputs/local_sim.log", help="Path for the output sim log")
    args = parser.parse_args()
    
    generate_log_from_historical(args.data, args.out)