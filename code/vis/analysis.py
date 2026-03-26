import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import indicators

def load_data(data_dir):
    price_cols = ['day', 'timestamp', 'product', 'bid_price_1', 'bid_volume_1', 'bid_price_2', 'bid_volume_2', 'bid_price_3', 'bid_volume_3', 'ask_price_1', 'ask_volume_1', 'ask_price_2', 'ask_volume_2', 'ask_price_3', 'ask_volume_3', 'mid_price', 'profit_and_loss']
    
    price_dfs = []
    trade_dfs = []
    
    for file in glob.glob(os.path.join(data_dir, "prices_round_0_day_*.csv")):
        df = pd.read_csv(file, sep=';')
        price_dfs.append(df)
        
    for file in glob.glob(os.path.join(data_dir, "trades_round_0_day_*.csv")):
        day_str = file.split('day_')[1].replace('.csv', '')
        day = int(day_str)
        df = pd.read_csv(file, sep=';')
        df['day'] = day
        trade_dfs.append(df)
        
    prices = pd.concat(price_dfs, ignore_index=True) if price_dfs else pd.DataFrame()
    trades = pd.concat(trade_dfs, ignore_index=True) if trade_dfs else pd.DataFrame()
    
    # Sort by day and timestamp
    if not prices.empty:
        prices.sort_values(['day', 'timestamp'], inplace=True)
    if not trades.empty:
        trades.sort_values(['day', 'timestamp'], inplace=True)
        # rename symbol to product in trades
        if 'symbol' in trades.columns:
            trades.rename(columns={'symbol': 'product'}, inplace=True)
        
    return prices, trades

def analyze_prices(prices, output_dir):
    results = {}
    for product, df in prices.groupby('product'):
        os.makedirs(os.path.join(output_dir, product), exist_ok=True)
        
        # Calculate some metrics
        df = df.copy()
        df['spread'] = df['ask_price_1'] - df['bid_price_1']
        df['mid'] = (df['ask_price_1'] + df['bid_price_1']) / 2.0
        
        # Add technical indicators
        df = indicators.add_bollinger_bands(df, column='mid_price', window=50, num_std=2)
        df = indicators.add_vwap(df)
        df = indicators.add_emas(df, column='mid_price', spans=[12, 26])
        
        # Volume imbalance
        df['bid_vol_total'] = df['bid_volume_1'].fillna(0) + df['bid_volume_2'].fillna(0) + df['bid_volume_3'].fillna(0)
        df['ask_vol_total'] = df['ask_volume_1'].fillna(0) + df['ask_volume_2'].fillna(0) + df['ask_volume_3'].fillna(0)
        df['vol_imbalance'] = (df['bid_vol_total'] - df['ask_vol_total']) / (df['bid_vol_total'] + df['ask_vol_total']).replace(0, 1)
        
        # Return and volatility
        df['mid_return'] = df['mid'].pct_change()
        
        stats = {
            'mean_spread': df['spread'].mean(),
            'max_spread': df['spread'].max(),
            'min_spread': df['spread'].min(),
            'volatility': df['mid_return'].std(),
            'mean_price': df['mid'].mean()
        }
        results[product] = stats
        
        df.to_csv(os.path.join(output_dir, product, 'prices_processed.csv'), index=False)
        
        # Plotting interactive indicators over sequential time instead of mid price overlays
        df['sequential_ts'] = df['day'] * 1_000_000 + df['timestamp']
        plot_df = df.iloc[::5] if len(df) > 10000 else df # downsample if needed for performance
        
        fig = go.Figure()
        
        # Best bid and ask bounds
        fig.add_trace(go.Scatter(x=plot_df['sequential_ts'], y=plot_df['bid_price_1'], mode='lines', name='Best Bid', line=dict(color='green', width=1), opacity=0.6))
        fig.add_trace(go.Scatter(x=plot_df['sequential_ts'], y=plot_df['ask_price_1'], mode='lines', name='Best Ask', line=dict(color='red', width=1), opacity=0.6))
        
        # Plot VWAP and BB
        fig.add_trace(go.Scatter(x=plot_df['sequential_ts'], y=plot_df['cum_vwap'], mode='lines', name='Daily Cumulative VWAP', line=dict(color='purple', width=2)))
        fig.add_trace(go.Scatter(x=plot_df['sequential_ts'], y=plot_df['BB_upper'], mode='lines', name='BB Upper', line=dict(color='orange', dash='dot', width=1)))
        fig.add_trace(go.Scatter(x=plot_df['sequential_ts'], y=plot_df['BB_lower'], mode='lines', name='BB Lower', line=dict(color='orange', dash='dot', width=1), fill='tonexty', fillcolor='rgba(255, 165, 0, 0.1)'))
        
        fig.update_layout(
            title=f'{product} Market Data & Active Indicators (Sequential)', 
            xaxis_title='Sequential Time (Day Offset + Timestamp)', 
            yaxis_title='Price',
            hovermode='x unified'
        )
        fig.write_html(os.path.join(output_dir, product, f'{product}_indicators_interactive.html'))
        
        # Static plots
        plt.figure(figsize=(10, 6))
        sns.histplot(df['spread'].dropna(), bins=20, kde=True)
        plt.title(f'{product} Spread Distribution')
        plt.savefig(os.path.join(output_dir, product, f'{product}_spread_dist.png'))
        plt.close()
        
    # Save global metrics
    pd.DataFrame(results).T.to_csv(os.path.join(output_dir, 'metrics_summary.csv'))
    return results

def analyze_trades(trades, output_dir):
    if trades.empty: return
    trades.to_csv(os.path.join(output_dir, 'trades_processed.csv'), index=False)
    
    summary = trades.groupby(['day', 'product']).agg(
        total_quantity=('quantity', 'sum'),
        mean_price=('price', 'mean'),
        trade_count=('price', 'count')
    ).reset_index()
    summary.to_csv(os.path.join(output_dir, 'trades_summary.csv'), index=False)
    
    # Static plots
    plt.figure(figsize=(10, 6))
    if not summary.empty:
        sns.barplot(data=summary, x='product', y='total_quantity', hue='day')
        plt.title('Total Trade Volume by Product and Day')
        plt.savefig(os.path.join(output_dir, 'trade_volume_bar.png'))
    plt.close()

if __name__ == "__main__":
    data_dir = "../../TUTORIAL_ROUND_1"
    output_dir = "../../outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading data...")
    prices, trades = load_data(data_dir)
    print(f"Loaded {len(prices)} price records and {len(trades)} trade records.")
    
    print("Analyzing prices...")
    price_stats = analyze_prices(prices, output_dir)
    print("Price stats:")
    print(pd.DataFrame(price_stats).T)
    
    print("Analyzing trades...")
    analyze_trades(trades, output_dir)
    print("Done. Outputs saved to", output_dir)
