# type: ignore
import logging
import os
import threading
from pathlib import Path
from typing import List

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs
from pydantic import BaseModel, ConfigDict, Field, confloat, conint, model_validator
from sortedcontainers import SortedDict
from binance_data_saver.data_objects import DepthEntry, StandardRow


# from binance_data_saver.utils.misc_utils import get_time_delta

log = logging.getLogger(__file__)

def get_row_labels():
    labels = []
    labels.pre

class ParquetSaver:

    def __init__(self, config):
        # current file root:
        self.root_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        self.abs_save_dir = self.root_dir / Path(config['save_dir'])
        if not os.path.exists(self.abs_save_dir):
            os.makedirs(self.abs_save_dir)
        
        if config['s3_bucket'] != '':
            self.s3_fs = s3fs.S3FileSystem()

        self.lock = threading.Lock()
        self.config = config
        self.time_to_row_data = SortedDict()
        self.save_every = config['n_events_per_write']
        self.iteration = 0
        self.colnames = None

    def reset_time_to_row_data(self):
        self.time_to_row_data = SortedDict()

    def ohlc_cb(self, data):
        # logging.info("ohlc", data)
        # # #logging.info("len time_to_row_data", len(self.time_to_row_data))
        event_time = int(data['E'])
        data_ohlc = data['k']
        if event_time in self.time_to_row_data:
            row: StandardRow = self.time_to_row_data[event_time]
        else:
            row = StandardRow(config=self.config)
        row.o = float(data_ohlc['o'])
        row.h = float(data_ohlc['h'])
        row.l = float(data_ohlc['l'])
        row.c = float(data_ohlc['c'])
        row.v = float(data_ohlc['v'])
        row.ohlc_time_start = int(data_ohlc['t'])
        row.ohlc_time_end = int(data_ohlc['T'])
        row.first_trade_id_ohlc = int(data_ohlc['f'])
        row.last_trade_id_ohlc = int(data_ohlc['L'])
        self.time_to_row_data[event_time] = row
        self.check_if_should_parquet_export()

    def depth_cb(self, data):
        # logging.info("depth", data)
        event_time = int(data['E'])
        # logging.info("E", event_time)
        #logging.info("Time delta depth", get_time_delta(event_time))
        bids = data['top_bids']
        asks = data['top_asks']
        if event_time in self.time_to_row_data:
            row = self.time_to_row_data[event_time]
        else:
            row = StandardRow(config=self.config)
        row.top_k_bids = [DepthEntry(price=float(x[0]), quantity=float(x[1])) \
                            for x in bids]
        row.top_k_asks = [DepthEntry(price=float(x[0]), quantity=float(x[1])) \
                            for x in asks]
        self.time_to_row_data[event_time] = row
        self.check_if_should_parquet_export()

    def agg_trades_cb(self, data):
        # logging.info("trades", data)
        event_time = int(data['E'])
        #logging.info("E", event_time)
        # logging.info(f"Time delta trades {int(data['m'])}")
        if event_time in self.time_to_row_data:
            row: StandardRow= self.time_to_row_data[event_time]
            if self.trade_exists_in_row(row):
                average_price = (row.quantity_trade * row.price_trade + \
                                    float(data['q']) * float(data['p'])) / \
                                    (row.quantity_trade + float(data['q']))
                data['q'] = row.quantity_trade + float(data['q'])
                data['p'] = average_price
                data['is_market_maker'] = -1
                # event_time += 1
        else:
            row: StandardRow = StandardRow(config=self.config)
        row.price_trade = float(data['p'])
        row.quantity_trade = float(data['q'])
        row.is_market_maker = int(data['m'])
        row.last_trade_id_aggtrade = int(data['l'])
        row.first_trade_id_aggtrade = int(data['f'])
        self.time_to_row_data[event_time] = row
        self.check_if_should_parquet_export()
    

    def aggregate_trade_row_and_new_aggTrade_event(self, row, data):
        self.time_to_row_data
        return row

    def trade_exists_in_row(self, row: StandardRow) -> bool:
        return row.quantity_trade > 0
    # def trades_cb(self, data):
    #     pass

    def get_colnames(self, time_to_row_items):
        if self.colnames is not None:
            return self.colnames
        else:
            self.colnames = ['Time_millis_times_10'] + \
                            time_to_row_items[0][1].get_names()
            return self.colnames

    def save_to_parquet(self):
        self.iteration += 1
        self.lock.acquire()
        items = self.time_to_row_data.items()
        self.reset_time_to_row_data()
        self.lock.release()
        # log.info(f"items: {items}")
        # log.info(f"first as array {items[0][1].as_array()}")
        arr = [[item[0], *item[1].as_array()] for item in items]
        try:
            print('colnames', self.get_colnames(items))
            pa_table = pa.Table.from_arrays(np.array(arr).T, self.get_colnames(items))
        except Exception as e:
            import ipdb; ipdb.set_trace()
        log.info(f"Saving to {self.abs_save_dir}/data_{self.iteration}.parquet")

        if self.config['s3_bucket'] != '':
            pq.write_table(pa_table, f"{s3_bucket}/data/data_{self.iteration}.parquet", \
                        compression=self.config['compression_type'], filesystem=self.s3_fs)
            print("wrote to s3")
        else:
            pq.write_table(pa_table, f"{self.abs_save_dir}/data_{self.iteration}.parquet", \
                        compression=self.config['compression_type'])
            print("wrote to local")

    def check_if_should_parquet_export(self):
        if len(self.time_to_row_data) > self.save_every:
            self.save_to_parquet()
