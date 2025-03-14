# Binance stream data saver

<div align="center">
  <img src="assets/depth_managing_demo.gif" width="50%" alt="Depth Managing Demo">
  <p><em>The animation shows 100 depth pairs that are maintained for ETHUSDT and optionally saved (indexed by unix time)</em></p>
</div>

### Saving logic:
- Maintain depthbook for specific token and collect depth data (see visualization section)
- Receive trades, OHLC stream and save it as well  
After the `n_events_per_write` is received from stream the data is saved to directory. See the `./binance_data_saver/config.yaml`.

### Running locally
```
poetry install && poetry shell
```
Running the data saving:

````
python binance_data_saver/main.py
````
### Visualization
To visualize how the depthbook is managed run this, remember to adjust `./binance_data_saver/config.yaml` `n_depth_cols`:
```
python binance_data_saver/manage_ws_depth.py
```
