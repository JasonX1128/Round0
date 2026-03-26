import json
from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    def __init__(self):
        self.POSITION_LIMIT_EMERALDS = 80
        self.POSITION_LIMIT_TOMATOES = 80

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        
        trader_data = state.traderData if state.traderData else "{}"
        try:
            trader_state = json.loads(trader_data)
        except Exception:
            trader_state = {"tomatoes_history": []}
            
        if "tomatoes_history" not in trader_state:
            trader_state["tomatoes_history"] = []

        # ========================================================
        # STRATEGY 1: EMERALDS - Pennying / Market Making
        # ========================================================
        # Provide liquidity at top of the orderbook
        product = "EMERALDS"
        if product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            pos = state.position.get(product, 0)
            
            if len(order_depth.sell_orders) > 0 and len(order_depth.buy_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                
                # Protect downside via arbitrage limit if extremely mispriced
                if best_ask < 10000:
                    buy_qty = min(-order_depth.sell_orders[best_ask], self.POSITION_LIMIT_EMERALDS - pos)
                    if buy_qty > 0:
                        orders.append(Order(product, best_ask, buy_qty))
                        pos += buy_qty
                if best_bid > 10000:
                    sell_qty = min(order_depth.buy_orders[best_bid], pos + self.POSITION_LIMIT_EMERALDS)
                    if sell_qty > 0:
                        orders.append(Order(product, best_bid, -sell_qty))
                        pos -= sell_qty
                        
                # Provide liquidity by being the BEST bid/ask inside the spread, bounded by exact margin.
                bid_price = min(best_bid + 1, 9993) # ensure we don't quote worse than +/- 7 around 10k
                ask_price = max(best_ask - 1, 10007)
                
                # Check limits securely before fulfilling liquidity quote
                if pos < self.POSITION_LIMIT_EMERALDS:
                    orders.append(Order(product, bid_price, self.POSITION_LIMIT_EMERALDS - pos))
                if pos > -self.POSITION_LIMIT_EMERALDS:
                    orders.append(Order(product, ask_price, -(pos + self.POSITION_LIMIT_EMERALDS)))
            
            result[product] = orders

        # ========================================================
        # STRATEGY 2: TOMATOES - Drift Reversion / Pennying 
        # ========================================================
        # Taking Market explicitly bleeds spread fees. Instead of taking market, we drift limit orders around SMA momentum.
        product = "TOMATOES"
        if product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            pos = state.position.get(product, 0)
            
            if len(order_depth.sell_orders) > 0 and len(order_depth.buy_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                mid_price = (best_ask + best_bid) / 2.0
                
                trader_state["tomatoes_history"].append(mid_price)
                if len(trader_state["tomatoes_history"]) > 9:
                    trader_state["tomatoes_history"].pop(0)
                    
                if len(trader_state["tomatoes_history"]) == 9:
                    sma = sum(trader_state["tomatoes_history"]) / 9.0
                    
                    # We will market make around the SMA to avoid crossing spread fees
                    # Quote slightly better/worse than SMA depending on our position
                    bid_price = int(sma - 5)
                    ask_price = int(sma + 5)
                    
                    # Limit to top of book (so we aren't buried inside the spread paying for taker fees)
                    bid_price = min(bid_price, best_bid + 1)
                    ask_price = max(ask_price, best_ask - 1)
                    
                    if pos < self.POSITION_LIMIT_TOMATOES:
                        orders.append(Order(product, bid_price, self.POSITION_LIMIT_TOMATOES - pos))
                    if pos > -self.POSITION_LIMIT_TOMATOES:
                        orders.append(Order(product, ask_price, -(pos + self.POSITION_LIMIT_TOMATOES)))

            result[product] = orders

        # Format and output updated state configuration 
        state_data_str = json.dumps(trader_state)
        return result, conversions, state_data_str