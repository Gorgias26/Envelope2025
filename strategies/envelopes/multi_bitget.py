import datetime
import sys

sys.path.append("./Live-Tools-V2-main 2025")

import asyncio
from utilities.bitget_perp import PerpBitget
from secret import ACCOUNTS
import ta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


 ######## SL 5% du l'envelope n°2
 ######## trailing 3% 
 ## TP  4,6,8,10,12%
 ## Verifier si la quantité du trainling = quantité de la position 
 ## Ou ouvrire 5 trailing pour chaque TP pour pas avoir le probleme du trainling qui marche pas car la quantité corespond pas.






async def main():
    account = ACCOUNTS["bitget1"]

    margin_mode = "crossed"  # isolated or crossed
    leverage = 1
    hedge_mode = True # Warning, set to False if you are in one way mode
    tf = "1h"
    sl = 0.4
    params = {
        "DOGE/USDT": {
            "src": "high",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.07, 0.09],
            "size": 1.0,
            "trailing": 3.0,
            "sides": ["long"],
        },
    }

    exchange = PerpBitget(
        public_api=account["public_api"],
        secret_api=account["secret_api"],
        password=account["password"],
    )
    invert_side = {"long": "sell", "short": "buy"}
    print(
        f"--- Execution started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )
    try:
        await exchange.load_markets()
        pairs = list(params.keys())

        print(f"Getting data and indicators on {len(pairs)} pairs...")
        tasks = [exchange.get_last_ohlcv(pair, tf, 50) for pair in pairs]
        dfs = await asyncio.gather(*tasks)
        df_list = dict(zip(pairs, dfs))

        for pair in df_list:
            current_params = params[pair]
            df = df_list[pair]
            if current_params["src"] == "close":
                src = df["close"]
            elif current_params["src"] == "ohlc4":
                src = (df["close"] + df["high"] + df["low"] + df["open"]) / 4

            df["ma_base"] = ta.trend.sma_indicator(
                close=src, window=current_params["ma_base_window"]
            )
            high_envelopes = [
                round(1 / (1 - e) - 1, 3) for e in current_params["envelopes"]
            ]
            for i in range(1, len(current_params["envelopes"]) + 1):
                df[f"ma_high_{i}"] = df["ma_base"] * (1 + high_envelopes[i - 1])
                df[f"ma_low_{i}"] = df["ma_base"] * (
                    1 - current_params["envelopes"][i - 1]
                )

            df_list[pair] = df

        usdt_balance = await exchange.get_balance()
        usdt_balance = usdt_balance.total
        print(f"Balance: {round(usdt_balance, 2)} USDT")

        tasks = [exchange.get_open_trigger_orders(pair) for pair in pairs]
        
        
        
         #  CANCEL TRIGGER ORDER
        
        
        print(f"Getting open trigger orders...")
        trigger_orders = await asyncio.gather(*tasks)
        trigger_order_list = dict(
            zip(pairs, trigger_orders)
        )  # Get all open trigger orders by pair

        tasks = []
        for pair in df_list:
            params[pair]["canceled_orders_buy"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            params[pair]["canceled_orders_sell"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "sell" and order.reduce is False)
                ]
            )
            tasks.append(
                exchange.cancel_trigger_orders(
                    pair, [order.id for order in trigger_order_list[pair]]
                )
            )

        print(f"Canceling trigger orders...")
        await asyncio.gather(*tasks)  # Cancel all trigger orders




         #  CANCEL LIMITE ORDER REDUCE ONLY FALSE

        # tasks = [exchange.get_open_orders(pair) for pair in pairs]
        # print(f"Getting open orders...")
        # orders = await asyncio.gather(*tasks)
        # order_list = dict(zip(pairs, orders))  # Get all open orders by pair

        # tasks = []
        # for pair in df_list:
            # params[pair]["canceled_orders_buy"] = params[pair][
                # "canceled_orders_buy"
            # ] + len(
                # [
                    # order
                    # for order in order_list[pair]
                    # if (order.side == "buy" and order.reduce is False)
                # ]
            # )
            # params[pair]["canceled_orders_sell"] = params[pair][
                # "canceled_orders_sell"
            # ] + len(
                # [
                    # order
                    # for order in order_list[pair]
                    # if (order.side == "sell" and order.reduce is False)
                # ]
            # )
            # tasks.append(
                # exchange.cancel_orders(pair, [order.id for order in order_list[pair]])
            # )

        # print(f"Canceling limit orders...")
        # await asyncio.gather(*tasks)  # Cancel all orders




          # remplacer le SL par un trailing stop
          # Rajouter des TP a 2 , 4 , 6 , 8 , 10
          # si position = 0 viré les trailing et limite order.
          # si position = 1 ne pas mettre de trailing et TP
         #  GET POSITION AND SL


        print(f"Getting live positions...")
        positions = await exchange.get_open_positions(pairs)
        tasks_close = []
        tasks_open = []
        for position in positions:
            print(
                f"Current position on {position.pair} {position.side} - {position.size} ~ {position.usd_size} $"
            )
            if position.side == "long":
                sl_side = "sell"
                sl_price = exchange.price_to_precision(
                    position.pair, position.entry_price * (1 - sl)
                )
            elif position.side == "short":
                sl_side = "buy"
                sl_price = exchange.price_to_precision(
                    position.pair, position.entry_price * (1 + sl)
                )
                
            # Trailing STOP 
            params = {'oneWayMode': False,'reduceOnly': True,'trailingTriggerPrice': exchange.price_to_precision(position.pair, StopPrice),'trailingPercent': Trailing,'triggerType': "fill_price",}
            order = exchange.create_order(position.pair, "market", sl_side, position.size , params=params)   
            
            
            
            
            
            # limite order
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_buy"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="buy",
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"]
                        ),
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_low_{i+1}"] * 1.005
                        ),
                        size=exchange.amount_to_precision(
                            position.pair,
                            (
                                (params[position.pair]["size"] * usdt_balance)
                                / len(params[position.pair]["envelopes"])
                                * leverage
                            )
                            / row[f"ma_low_{i+1}"],
                        ),
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        hedge_mode=hedge_mode,
                        error=False,
                    )
                )
            for i in range(
                len(params[position.pair]["envelopes"])
                - params[position.pair]["canceled_orders_sell"],
                len(params[position.pair]["envelopes"]),
            ):
                tasks_open.append(
                    exchange.place_trigger_order(
                        pair=position.pair,
                        side="sell",
                        trigger_price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"] * 0.995
                        ),
                        price=exchange.price_to_precision(
                            position.pair, row[f"ma_high_{i+1}"]
                        ),
                        size=exchange.amount_to_precision(
                            position.pair,
                            (
                                (params[position.pair]["size"] * usdt_balance)
                                / len(params[position.pair]["envelopes"])
                                * leverage
                            )
                            / row[f"ma_high_{i+1}"],
                        ),
                        type="limit",
                        reduce=False,
                        margin_mode=margin_mode,
                        hedge_mode=hedge_mode,
                        error=False,
                    )
                )
        print(f"Placing {len(tasks_close)} close SL / limit order...")
        await asyncio.gather(*tasks_close)  # Limit orders when in positions











         #  LIMITE ORDER OPEN


        pairs_not_in_position = [
            pair
            for pair in pairs
            if pair not in [position.pair for position in positions]
        ]
        for pair in pairs_not_in_position:
            row = df_list[pair].iloc[-2]
            for i in range(len(params[pair]["envelopes"])):
                if "long" in params[pair]["sides"]:
                    tasks_open.append(
                        exchange.place_trigger_order(
                            pair=pair,
                            side="buy",
                            price=exchange.price_to_precision(
                                pair, row[f"ma_low_{i+1}"]
                            ),
                            trigger_price=exchange.price_to_precision(
                                pair, row[f"ma_low_{i+1}"] * 1.005
                            ),
                            size=exchange.amount_to_precision(
                                pair,
                                (
                                    (params[pair]["size"] * usdt_balance)
                                    / len(params[pair]["envelopes"])
                                    * leverage
                                )
                                / row[f"ma_low_{i+1}"],
                            ),
                            type="limit",
                            reduce=False,
                            margin_mode=margin_mode,
                            hedge_mode=hedge_mode,
                            error=False,
                        )
                    )
                if "short" in params[pair]["sides"]:
                    tasks_open.append(
                        exchange.place_trigger_order(
                            pair=pair,
                            side="sell",
                            trigger_price=exchange.price_to_precision(
                                pair, row[f"ma_high_{i+1}"] * 0.995
                            ),
                            price=exchange.price_to_precision(
                                pair, row[f"ma_high_{i+1}"]
                            ),
                            size=exchange.amount_to_precision(
                                pair,
                                (
                                    (params[pair]["size"] * usdt_balance)
                                    / len(params[pair]["envelopes"])
                                    * leverage
                                )
                                / row[f"ma_high_{i+1}"],
                            ),
                            type="limit",
                            reduce=False,
                            margin_mode=margin_mode,
                            hedge_mode=hedge_mode,
                            error=False,
                        )
                    )

        print(f"Placing {len(tasks_open)} open limit order...")
        await asyncio.gather(*tasks_open)  # Limit orders when not in positions
















        await exchange.close()
        print(
            f"--- Execution finished at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
        )
    except Exception as e:
        await exchange.close()
        raise e


if __name__ == "__main__":
    asyncio.run(main())
