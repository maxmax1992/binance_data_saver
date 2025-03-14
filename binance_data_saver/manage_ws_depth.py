# class to manage websocket depth data according to
# https://binance-docs.github.io/apidocs/spot/en/#how-to-manage-a-local-order-book-correctly
#  type: ignore
import os
import threading
import time
import warnings
from datetime import datetime
from json import loads
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import requests
import seaborn as sns
import websocket
from websocket import WebSocketApp
import yaml
from sortedcontainers import SortedDict

# Filter out the specific pandas FutureWarning about use_inf_as_na
warnings.filterwarnings("ignore", message="use_inf_as_na option is deprecated", category=FutureWarning)

sns.set_theme()
DEBUG = False


class DepthCacheManager:
    """
    Class that manages depth cache according to the binance docs
    """

    def __init__(self, config: Dict, should_plot=True):
        # create websocket connection
        self.config = config
        self.should_plot = should_plot

    def _flatten(self, list_of_lists: List):
        return [item for sublist in list_of_lists for item in sublist]

    def _get_time_string(self) -> str:
        return datetime.utcnow().strftime("%F %T.%f")[:-3]

    def initialize_socket_and_params(self, token: str, update_rate_ms: int) -> None:
        self.ws = self.initialize_socket(token, update_rate_ms)
        self.initialize_params(token)

    def initialize_socket(self, token, update_rate_ms):
        return WebSocketApp(
            url=f"wss://stream.binance.com:9443/ws/{token}@depth@{update_rate_ms}ms",
            on_message=self.on_message,
            on_error=self.on_error,
        )

    def initialize_params(self, token):
        """initialize params"""
        self.token = token
        self.orderbook = {}
        self.updates = 0
        self.ax, self.fig = None, None
        self.asks_plot, self.bids_plot = None, None
        if self.should_plot:
            self.init_plot()
        self.xlims = (None, None)
        self.bounds = [None, None]

    def clear_plot(self):
        if len(self.ax.lines) > 0:
            # print("n_lines: ", len(self.ax.lines))
            while len(self.ax.lines) > 0:
                self.ax.lines[len(self.ax.lines) - 1].remove()
        # # print("returning")

    def init_plot(self):
        plt.ion()
        # to run GUI event loop
        # here we are creating sub plots

        self.fig, self.ax = plt.subplots()
        # Set the y-axis to start at the middle of the chart
        bids_x = np.linspace(1100, 1200, 5)
        bids_y = np.random.randint(1, 50, 5)

        asks_x = np.linspace(1201, 1400, 5)
        asks_y = np.random.randint(1, 50, 5)

        sns.ecdfplot(
            x=bids_x,
            weights=bids_y,
            stat="count",
            color="red",
            complementary=True,
            ax=self.ax,
        )
        sns.ecdfplot(x=asks_x, weights=asks_y, stat="count", color="blue", ax=self.ax)
        # Add a legend and show the plot
        self.ax.ticklabel_format(useOffset=False, style="plain")

    def get_plot_bids_n_asks(self) -> (List, List, List, List):
        arr_1 = self.orderbook["bids"]
        arr_2 = self.orderbook["asks"]
        arr1, arr2 = list(arr_1.items()), list(arr_2.items())
        bids_x, bids_y = [], []
        asks_x, asks_y = [], []

        for bid_v, bid_q in arr1[: min(len(arr1), self.config["n_depth_pairs"])]:
            # Skip infinite values
            if np.isinf(bid_v) or np.isinf(bid_q):
                continue
            bids_x.append(bid_v)
            bids_y.append(bid_q)

        for ask_v, ask_q in arr2[: min(len(arr2), self.config["n_depth_pairs"])]:
            # Skip infinite values
            if np.isinf(ask_v) or np.isinf(ask_q):
                continue
            asks_x.append(ask_v)
            asks_y.append(ask_q)

        return bids_x, bids_y, asks_x, asks_y

    def plot_orderbook(self) -> None:
        if not self.should_plot:
            return
        bids_x, bids_y, asks_x, asks_y = self.get_plot_bids_n_asks()

        self.clear_plot()

        # Make sure we have data to plot
        if not bids_x or not asks_x:
            return

        # Update assert to check if we have any data, not requiring exact counts
        assert len(bids_x) == len(bids_y) and len(asks_x) == len(asks_y), "invalid len"

        sns.ecdfplot(
            x=bids_x,
            weights=bids_y,
            stat="count",
            color="red",
            complementary=True,
            ax=self.ax,
        )
        sns.ecdfplot(x=asks_x, weights=asks_y, stat="count", color="blue", ax=self.ax)

        self.ax.relim(True)
        # Update the plot
        # ax.autoscale_view()
        # drawing updated values
        self.fig.canvas.draw()
        # This will run the GUI event
        # loop until all UI events
        # currently waiting have been processed
        self.fig.canvas.flush_events()
        time.sleep(0.01)

    # def save_bids_n_asks(self, bids, asks, lastUpdateId, fname):
    #     bids = self._flatten([[key, value] for key, value in bids.items()])
    #     asks = self._flatten([[-key, value] for key, value in asks.items()])
    #     csv_write_list = [lastUpdateId, *bids, *asks]
    #     self._write_row(csv_write_list, fname)

    def get_snapshots(self):
        while True:
            snapshot = self.get_snapshot()

            snapshot["bids"] = [(float(x[0]), float(x[1])) for x in snapshot["bids"]]
            snapshot["asks"] = [(float(x[0]), float(x[1])) for x in snapshot["asks"]]

            bids = {b[0]: b[1] for b in snapshot["bids"]}
            asks = {b[0]: b[1] for b in snapshot["asks"]}

            snapshot["bids"] = SortedDict(lambda x: -x)
            snapshot["bids"].update(bids)
            snapshot["asks"] = SortedDict(asks)
            # print("snapsho bids: ", snapshot["bids"].items())
            # print("snapshot asks: ", snapshot["asks"].items())

            # bids_tuple_arr = snapshot["bids"].items()
            # for i in (1, len(bids_tuple_arr) - 1):
            #     assert float(bids_tuple_arr[i][0]) < float(bids_tuple_arr[i - 1][0])

            # asks_tuple_arr = snapshot["asks"].items()
            # for i in (1, len(asks_tuple_arr) - 1):
            #     assert float(asks_tuple_arr[i][0]) > float(asks_tuple_arr[i - 1][0])

            self.bounds = [
                snapshot["bids"].items()[len(snapshot["asks"]) - 1][0],
                snapshot["asks"].items()[len(snapshot["asks"]) - 1][0],
            ]
            time.sleep(1)

    # keep connection alive
    def run_forever(self, update_callback, token, update_rate_ms) -> None:
        assert (
            update_rate_ms == 1000 or update_rate_ms == 100
        ), "invalid update rate, must be 100 or 1000"

        # update_rate_ms = 100
        self.initialize_socket_and_params(token, update_rate_ms)
        self.update_callback = update_callback

        t2 = threading.Thread(target=self.get_snapshots)
        t2.start()

        self.ws.run_forever()
        # # print("AFTER RUNniNG FOREVER")

    def init_from_snapshot(self) -> None:
        self.orderbook = self.get_snapshot()
        self.orderbook["bids"] = [
            (float(x[0]), float(x[1])) for x in self.orderbook["bids"]
        ]
        self.orderbook["asks"] = [
            (float(x[0]), float(x[1])) for x in self.orderbook["asks"]
        ]

        bids = {b[0]: b[1] for b in self.orderbook["bids"]}
        asks = {b[0]: b[1] for b in self.orderbook["asks"]}

        self.orderbook["bids"] = SortedDict(lambda x: -x)
        self.orderbook["bids"].update(bids)
        self.orderbook["asks"] = SortedDict(asks)
        self.bounds = [
            self.orderbook["bids"].items()[len(self.orderbook["asks"]) - 1][0],
            self.orderbook["asks"].items()[len(self.orderbook["asks"]) - 1][0],
        ]
        self.plot_orderbook()

    def on_message(self, ws, message) -> None:
        data = loads(message)
        if len(self.orderbook) == 0:
            self.init_from_snapshot()
        lastUpdateId = self.orderbook["lastUpdateId"]

        if self.updates == 0:
            if data["U"] <= lastUpdateId + 1 and data["u"] >= lastUpdateId + 1:
                self.process_updates(data)
                self.orderbook["lastUpdateId"] = data["u"]
            else:
                pass
        elif data["U"] == lastUpdateId + 1:
            self.process_updates(data)
            self.orderbook["lastUpdateId"] = data["u"]
        else:
            pass

    def validate_orderbook(self) -> None:
        pass

    def process_updates(self, data: Dict) -> None:
        for update in data["b"]:
            self.manage_orderbook("bids", update)
        for update in data["a"]:
            self.manage_orderbook("asks", update)

        # data['orderbook'] = self.orderbook
        # print(self.orderbook['bids'])
        self.update_callback(
            {
                "E": data["E"],
                "top_bids": list(self.orderbook["bids"].items())[
                    : self.config["n_depth_pairs"]
                ],
                "top_asks": list(self.orderbook["asks"].items())[
                    : self.config["n_depth_pairs"]
                ],
            }
        )
        if self.should_plot:
            self.plot_orderbook()

    def manage_orderbook(self, side: str, update: str) -> None:
        price, qty = float(update[0]), float(update[1])
        if price in self.orderbook[side]:
            if float(qty) == 0:
                del self.orderbook[side][price]
            else:
                self.orderbook[side][price] = qty
        else:
            if float(qty) != 0:
                self.orderbook[side][price] = qty

    def on_error(self, ws: WebSocketApp, error: Exception) -> None:
        raise error

    def get_snapshot(self) -> Dict[str, str]:
        r = requests.get(
            f"https://api.binance.com/api/v3/depth?symbol={self.token.upper()}"
            + f"&limit={int(self.config['n_depth_pairs']*1.5)}",
            # seconds
            timeout=3,
        )
        ret_data = loads(r.content.decode())
        return ret_data


if __name__ == "__main__":
    # create webscocket client
    # TODO -> validate the data using the snapshots
    # TODO -> option to save the data, instead of plotting
    client = None
    token = "ethusdt"
    update_rate = 100
    try:
        WORK_DIR = os.path.dirname(os.path.realpath(__file__))
        datasaver_config = {}
        with open(os.path.join(WORK_DIR, "config.yaml"), "r") as f:
            datasaver_config = yaml.load(f, Loader=yaml.FullLoader)
        client = DepthCacheManager(datasaver_config, should_plot=True)
        client.run_forever(lambda x: x, "ethusdt", update_rate)
    except KeyboardInterrupt:
        pass
