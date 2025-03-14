# Saving Binance stream data locally or to a s3 bucket

### Saving logic:
- Maintain depthbook for specific token and collect depth data
- Receive trades and ohlc stream and save it as well  
After the `n_events_per_write` is received from stream the data is saved to directory. See the `./binance_data_saver/config.yaml`.

### Running locally
```
poetry install && poetry shell
```
Running the data saving:

````
python binance_data_saver/main.py
````
To visualize how the depthbook is managed run this, remember to adjust `./binance_data_saver/config.yaml` `n_depth_cols`:
```
python binance_data_saver/manage_ws_depth.py
```