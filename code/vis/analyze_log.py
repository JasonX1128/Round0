import json
import pandas as pd
import io
import os
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def analyze_log(log_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    with open(log_path, 'r') as f:
        data = json.load(f)
        
    # 1. Parse activitiesLog (PnL, Position, Mid Price history of the run)
    activities_csv = data['activitiesLog']
    df_act = pd.read_csv(io.StringIO(activities_csv), sep=';')
    
    # 2. Parse trades
    trades = data.get('tradeHistory', [])
    df_trades = pd.DataFrame(trades)
    
    df_act['timestamp'] = pd.to_numeric(df_act['timestamp'])
    # Add sequential time if multiple days exist
    if 'day' in df_act.columns:
        df_act['seq_time'] = df_act['day'] * 1_000_000 + df_act['timestamp']
    else:
        df_act['seq_time'] = df_act['timestamp']
    
    # Plotting PnL
    fig = go.Figure()
    total_pnl = 0
    pnl_records = []
    
    for product in df_act['product'].unique():
        prod_df = df_act[df_act['product'] == product].sort_values('seq_time')
        # PnL trace
        fig.add_trace(go.Scatter(x=prod_df['seq_time'], y=prod_df['profit_and_loss'], mode='lines', name=f'{product} PnL'))
        
        # Calculate metric
        final_pnl = prod_df['profit_and_loss'].iloc[-1] if not prod_df.empty else 0
        total_pnl += final_pnl
        pnl_records.append({'Product': product, 'Final PnL': final_pnl})
        
        # Create a detailed per-product execution chart
        prod_trades = df_trades[df_trades['symbol'] == product].copy() if not df_trades.empty and 'symbol' in df_trades.columns else pd.DataFrame()
        
        # NOTE: The tradeHistory array only has 'timestamp', no 'day' property.
        # This causes misalignment in multi-day logs. We must map the sequence time.
        # We assume the log outputs trades monotonically. For multi-day continuity, 
        # we can cross-reference the activities log to infer the current day.
        # Simplest fix: Add the day base from when the timestamp wraps around or matches activities
        
        if not prod_trades.empty:
            # We construct a matching structure by matching timestamp values.
            # However, if there are identical timestamps across days, we need a smarter cumulative merge.
            # A simple monotonically increasing offset:
            current_day_offset = df_act['seq_time'].min() - df_act['timestamp'].min()
            last_ts = -1
            seq_times = []
            for ts in prod_trades['timestamp']:
                if ts < last_ts: # Day wrapped around
                    current_day_offset += 1_000_000
                seq_times.append(ts + current_day_offset)
                last_ts = ts
            prod_trades['seq_time'] = seq_times
            
        create_product_execution_plot(prod_df, prod_trades, product, output_dir)
        
    fig.update_layout(title=f'Strategy PnL Over Time - Total: {total_pnl:.2f}', xaxis_title='Sequential Time', yaxis_title='PnL')
    fig.write_html(os.path.join(output_dir, 'strategy_pnl.html'))
    
    # Save Trade summary
    if not df_trades.empty:
        df_trades.to_csv(os.path.join(output_dir, 'trades_executed.csv'), index=False)
        trade_summary = df_trades.groupby('symbol').agg(
            trades_count=('price', 'count'),
            mean_price=('price', 'mean'),
            total_vol=('quantity', 'sum')
        )
        trade_summary.to_csv(os.path.join(output_dir, 'trade_execution_summary.csv'))
        print("\n--- Trade Summary ---")
        print(trade_summary)

    print("\n--- PnL Summary ---")
    print(pd.DataFrame(pnl_records))
    print(f"TOTAL PNL: {total_pnl:.2f}")


def create_product_execution_plot(prod_df, trades_df, product, output_dir):
    """Plots mid price, fills, and bounds to visualize what the bot did."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Plot Mid Price
    fig.add_trace(go.Scatter(x=prod_df['seq_time'], y=prod_df['mid_price'], name='Mid Price', line=dict(color='gray', width=1)), secondary_y=False)
    
    # Map trades
    if not trades_df.empty:
        # A buy trade means we BOUGHT (buyer == 'SUBMISSION' or buyer == '') depending on perspective
        # Based on log snippet, buyer='SUBMISSION' means we bought, seller='SUBMISSION' means we sold
        buys = trades_df[trades_df['buyer'] == 'SUBMISSION']
        sells = trades_df[trades_df['seller'] == 'SUBMISSION']
        
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys['seq_time'], y=buys['price'], mode='markers', name='Buy Exec', marker=dict(color='green', symbol='triangle-up', size=8)), secondary_y=False)
            
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells['seq_time'], y=sells['price'], mode='markers', name='Sell Exec', marker=dict(color='red', symbol='triangle-down', size=8)), secondary_y=False)
    
    fig.update_layout(title=f'{product} Executions', xaxis_title='Time', yaxis_title='Price')
    fig.write_html(os.path.join(output_dir, f'{product}_executions.html'))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze Prosperity trading log")
    parser.add_argument("--log", type=str, default="../../results/round0/23792.log", help="Path to the log file (e.g. 23792.log)")
    parser.add_argument("--out", type=str, default="../../outputs/backtest_analysis", help="Path to the output directory")
    args = parser.parse_args()
    
    analyze_log(args.log, args.out)