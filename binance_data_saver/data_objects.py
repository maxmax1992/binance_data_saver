# type: ignore
from typing import List
from pydantic import BaseModel, ConfigDict, Field, confloat, conint, model_validator

class DepthEntry(BaseModel):
    price: confloat(ge=0) = 0
    quantity: confloat(ge=0) = 0

class StandardRow(BaseModel):
    model_config = ConfigDict(strict=True, \
                              arbitrary_types_allowed=True)
    config: dict
    o: confloat(ge=0) = 0
    h: confloat(ge=0) = 0
    l: confloat(ge=0) = 0
    c: confloat(ge=0) = 0
    v: confloat(ge=0) = 0

    ohlc_time_start: conint(ge=0) = 0
    ohlc_time_end: conint(ge=0) = 0

    first_trade_id_ohlc: conint(ge=-1) = 0
    last_trade_id_ohlc: conint(ge=-1) = 0

    price_trade: confloat(ge=0) = 0
    quantity_trade: confloat(ge=0) = 0

    is_market_maker: conint(ge=-1, le=1) = -1

    first_trade_id_aggtrade: conint(ge=0) = 0
    last_trade_id_aggtrade: conint(ge=0) = 0

    top_k_bids: List[DepthEntry] = Field(default_factory=list)
    top_k_asks: List[DepthEntry] = Field(default_factory=list)

    def model_post_init(self, __context):
        self.top_k_bids = [DepthEntry()] * self.config["n_depth_pairs"]
        self.top_k_asks = [DepthEntry()] * self.config["n_depth_pairs"]
    
    @model_validator(mode='after')
    def check_alphanumeric(self) -> 'StandardRow':
        assert len(self.top_k_asks) > 0, "values must be non-empty"
        assert len(self.top_k_bids) > 0, "values must be non-empty"
        assert len(self.top_k_asks) == self.config['n_depth_pairs'], "top_k_asks must be of length n_depth_pairs"
        assert len(self.top_k_bids) == self.config['n_depth_pairs'], "top_k_bids must be of length n_depth_pairs"
        last_entries = list(self.model_fields.keys())[-2:]
        for attr in last_entries:
            assert "top_k" in attr, "last entries must be top_k (depth entries)"
        return self

    def as_array(self):
        fields = self.model_fields
        values = []
        for attr in fields.keys():
            if attr == "config" or "top_k" in attr:
                continue
            values.append(getattr(self, attr))
        for i in range(self.config['n_depth_pairs']):
            values.append(self.top_k_bids[i].price)
            values.append(self.top_k_bids[i].quantity)

        for i in range(self.config['n_depth_pairs']): 
            values.append(self.top_k_asks[i].price)
            values.append(self.top_k_asks[i].quantity)
        return values

    def get_depth_side_name_given_side_data_and_name(self, side_data: List[DepthEntry], 
                                                     side_name: str) -> list[str]:
        side_names = [ f"{side_name}_{attr}_{i}" for i, depth_entry in enumerate(side_data) \
                        for attr in depth_entry.model_fields.keys()]
        return side_names

    def get_names(self):
        names = [x for x in self.model_fields.keys() if x != "config" and "top_k" not in x]
        depth_bid_names = self.get_depth_side_name_given_side_data_and_name(
            self.top_k_bids, 
            "bid"
        )
        depth_ask_names = self.get_depth_side_name_given_side_data_and_name(
            self.top_k_asks, 
            "ask"
        )
        return names + depth_bid_names + depth_ask_names