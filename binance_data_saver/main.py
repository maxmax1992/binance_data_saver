# type: ignore
import os
from typing import Dict

import yaml
import logging
from binance import ThreadedWebsocketManager

from binance_data_saver.manage_ws_depth import DepthCacheManager
from binance_data_saver.parquet_saver import ParquetSaver

WORK_DIR = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(level = logging.INFO)
log = logging.getLogger(__file__)

class CryptoTokenDataCollector:
    def __init__(self, symbol: str, api_key: str, api_secret: str, config: Dict):
        self.symbol = symbol.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.twm_kline_interval = "1s"
        self.config = config
        self.init_collectors(config)

    def init_collectors(self, config: Dict) -> None:
        self.twm = ThreadedWebsocketManager(
            api_key=self.api_key, api_secret=self.api_secret
        )
        self.depth_cache_manager = DepthCacheManager(
            config=self.config, should_plot=config["should_plot_depth"]
        )

    def start_data_collection(self, data_handler: ParquetSaver) -> None:
        self.twm.start()
        self.twm.start_kline_socket(
            callback=data_handler.ohlc_cb,
            symbol=self.symbol,
            interval=self.twm_kline_interval,
        )
        self.twm.start_aggtrade_socket(
            callback=data_handler.agg_trades_cb, symbol=self.symbol
        )
        self.depth_cache_manager.run_forever(
            data_handler.depth_cb, self.symbol, self.config["depth_update_rate"]
        )
        self.twm.join()

def load_config():
    config: Dict = {}
    with open(os.path.join(WORK_DIR, "config.yaml"), "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    print("ds config", config)
    return config

if __name__ == "__main__":
    # TODO add argparse
    # TODO add logging debug/info will print different things
    # TODO initialize from yaml file
    # TODO get the token info from envvars
    config = load_config()
    assert len(config) != 0, "Problem loading the config file"

    api_key = None # os.environ["BINANCE_API_KEY"]
    api_secret = None # os.environ["BINANCE_API_SECRET"]

    data_collector: CryptoTokenDataCollector = CryptoTokenDataCollector(
        "ETHUSDT",
        api_key,
        api_secret,
        config,
    )

    data_saver = ParquetSaver(config)
    data_collector.start_data_collection(data_saver)
