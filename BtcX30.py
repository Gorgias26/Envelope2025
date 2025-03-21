import datetime
import sys
import json
import os
import time
sys.path.append("./Envelope2025")

import asyncio
from utilities.bitget_perp import PerpBitget
from secret import ACCOUNTS
import ta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


 ######## SL 5% du l'envelope n°2
 # trailing 3% 
 ## TP  4,6,8,10,12%
 ## Verifier si la quantité du trainling = quantité de la position 
 ## Ou ouvrire 5 trailing pour chaque TP pour pas avoir le probleme du trainling qui marche pas car la quantité corespond pas.






async def main():
    account = ACCOUNTS["BtcX30"]

    # Charger les IDs des trailing stops existants
    trailing_stops_file = "trailing_stops.json"
    trailing_stops = {}
    if os.path.exists(trailing_stops_file):
        try:
            with open(trailing_stops_file, 'r') as f:
                trailing_stops = json.load(f)
        except:
            trailing_stops = {}

    margin_mode = "crossed"  # isolated or crossed
    leverage = 30
    hedge_mode = True # Warning, set to False if you are in one way mode
    tf = "1h"
    sl = 0.06
    trailing = 3
    trailing_step = 0.04
    trading_params = {
        "BTC/USDT": {
            "src": "close",
            "ma_base_window": 7,
            "envelopes": [0.05, 0.07, 0.09],
            "size": 1.0,
            "trailing": 3.0,
            "sides": ["long", "short"],
            "tp": [4, 6, 8, 10, 12],
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
        pairs = list(trading_params.keys())

        print(f"Getting data and indicators on {len(pairs)} pairs...")
        tasks = [exchange.get_last_ohlcv(pair, tf, 50) for pair in pairs]
        dfs = await asyncio.gather(*tasks)
        df_list = dict(zip(pairs, dfs))

        for pair in df_list:
            current_params = trading_params[pair]
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
            trading_params[pair]["canceled_orders_buy"] = len(
                [
                    order
                    for order in trigger_order_list[pair]
                    if (order.side == "buy" and order.reduce is False)
                ]
            )
            trading_params[pair]["canceled_orders_sell"] = len(
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

        print(f"Getting live positions...")
        positions = await exchange.get_open_positions(pairs)
        tasks_close = []
        tasks_open = []

        # Créer une liste des paires qui ont des positions ouvertes
        active_pairs = [position.pair for position in positions]

        # Nettoyer les trailing stops des positions fermées
        pairs_to_remove = []
        for pair in trailing_stops:
            if pair not in active_pairs:
                pairs_to_remove.append(pair)
                print(f"Position fermée pour {pair}, nettoyage du trailing stop")
        
        # Supprimer les trailing stops des positions fermées
        for pair in pairs_to_remove:
            try:
                old_trailing_id = trailing_stops[pair]
                await exchange.cancel_trigger_orders(pair, [old_trailing_id])
                print(f"Trailing stop annulé pour {pair}")
            except Exception as e:
                print(f"Erreur lors de l'annulation du trailing stop pour {pair}: {e}")
            del trailing_stops[pair]

        # Sauvegarder les modifications
        with open(trailing_stops_file, 'w') as f:
            json.dump(trailing_stops, f)

        for position in positions:
            print(
                f"Current position on {position.pair} {position.side} - {position.size} ~ {position.usd_size} $"
            )

            # Place SL
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

            await exchange.place_trigger_order(
                pair=position.pair,
                side=sl_side,
                trigger_price=sl_price,
                price=None,
                size=position.size,
                type="market",
                reduce=True,
                margin_mode=margin_mode,
                error=False,
            )
            # Gestion des trailing stops
            try:
                # Vérifier s'il y a déjà un trailing stop pour cette paire
                if position.pair in trailing_stops:
                    old_trailing_id = trailing_stops[position.pair]
                    try:
                        # Annuler l'ancien trailing stop
                        await exchange.cancel_trigger_orders(position.pair, [old_trailing_id])
                        print(f"Ancien trailing stop annulé pour {position.pair}")
                    except Exception as e:
                        print(f"Erreur lors de l'annulation de l'ancien trailing stop: {e}")
                    # Supprimer l'ID de la liste
                    del trailing_stops[position.pair]

                # Placer le nouveau trailing stop
                if position.side == "long":
                    StopPrice = exchange.price_to_precision(position.pair, position.entry_price * (1 + trailing_step))
                    params = {
                        'oneWayMode': False,
                        'reduceOnly': True,
                        'trailingTriggerPrice': StopPrice,
                        'trailingPercent': trailing,
                        'triggerType': "fill_price"
                    }
                    new_trailing = await exchange.place_trailing_stop(
                        pair=position.pair,
                        type="market",
                        side=sl_side,
                        size=position.size,
                        params=params
                    )
                    # Sauvegarder le nouvel ID
                    trailing_stops[position.pair] = new_trailing['info']['orderId']  # Accès à l'ID via info.orderId
                elif position.side == "short":
                    StopPrice = exchange.price_to_precision(position.pair, position.entry_price * (1 - trailing_step))
                    params = {
                        'oneWayMode': False,
                        'reduceOnly': True,
                        'trailingTriggerPrice': StopPrice,
                        'trailingPercent': trailing,
                        'triggerType': "fill_price"
                    }
                    new_trailing = await exchange.place_trailing_stop(
                        pair=position.pair,
                        type="market",
                        side=sl_side,
                        size=position.size,
                        params=params
                    )
                    # Sauvegarder le nouvel ID
                    print(f"Nouveau trailing stop créé: {new_trailing}")
                    trailing_stops[position.pair] = new_trailing['info']['orderId']  # Accès à l'ID via info.orderId

                # Sauvegarder les IDs dans le fichier
                with open(trailing_stops_file, 'w') as f:
                    json.dump(trailing_stops, f)

            except Exception as e:
                print(f"Erreur lors de la gestion des trailing stops: {e}")

            # Place Take Profits
            tp_size = position.size / len(trading_params[position.pair]["tp"])
            await asyncio.sleep(2)  # Attendre que la position soit complètement ouverte
            
            for tp_percent in trading_params[position.pair]["tp"]:
                try:
                    if position.side == "long":
                        tp_price = position.entry_price * (1 + tp_percent/100)
                        trigger_price = tp_price * 0.99  # 3% avant le TP
                        tp_side = "sell"
                    else:  # short
                        tp_price = position.entry_price * (1 - tp_percent/100)
                        trigger_price = tp_price * 1.01  # 3% avant le TP
                        tp_side = "buy"

                    # Formater les prix avec la bonne précision
                    formatted_trigger_price = exchange.price_to_precision(position.pair, trigger_price)
                    formatted_tp_price = exchange.price_to_precision(position.pair, tp_price)

                    # Placer l'ordre trigger pour le TP
                    await exchange.place_trigger_order(
                        pair=position.pair,
                        side=tp_side,
                        trigger_price=formatted_trigger_price,
                        price=formatted_tp_price,
                        size=tp_size,
                        type="limit",
                        reduce=True,
                        margin_mode=margin_mode,
                        error=False,
                    )
                    print(f"Placed TP at {tp_percent}% - Trigger Price: {formatted_trigger_price} - TP Price: {formatted_tp_price} - Size: {tp_size}")
                except Exception as e:
                    print(f"Error placing TP at {tp_percent}%: {str(e)}")
                    continue

            # limite open order
            for i in range(
                len(trading_params[position.pair]["envelopes"])
                - trading_params[position.pair]["canceled_orders_buy"],
                len(trading_params[position.pair]["envelopes"]),
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
                                (trading_params[position.pair]["size"] * usdt_balance)
                                / len(trading_params[position.pair]["envelopes"])
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
                len(trading_params[position.pair]["envelopes"])
                - trading_params[position.pair]["canceled_orders_sell"],
                len(trading_params[position.pair]["envelopes"]),
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
                                (trading_params[position.pair]["size"] * usdt_balance)
                                / len(trading_params[position.pair]["envelopes"])
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
            for i in range(len(trading_params[pair]["envelopes"])):
                if "long" in trading_params[pair]["sides"]:
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
                                    (trading_params[pair]["size"] * usdt_balance)
                                    / len(trading_params[pair]["envelopes"])
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
                if "short" in trading_params[pair]["sides"]:
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
                                    (trading_params[pair]["size"] * usdt_balance)
                                    / len(trading_params[pair]["envelopes"])
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
        print(f"Erreur rencontrée: {e}")


if __name__ == "__main__":
    asyncio.run(main())
