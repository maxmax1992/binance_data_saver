# ignore mypy typing
# type: ignore
import os
from typing import Dict, Optional

import yaml

WORK_DIR = os.path.dirname(os.path.realpath(__file__))

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FieldValidationInfo,
    ValidationError,
    field_validator,
    model_validator,
)


class ListNumber(BaseModel):
    model_config = ConfigDict(strict=True)
    value: int = Field(int, gt=0, lt=10)

class User(BaseModel):
    model_config = ConfigDict(strict=True, \
                              arbitrary_types_allowed=True)
    config: Dict
    name: str
    age: int = Field(int, ge=18, lt=30)
    is_active: bool
    values: list[ListNumber] = Field(default_factory=list)

    def model_post_init(self, attrs):
        print("in post init")
        self.values = [ListNumber()] * self.config['n_depth_pairs']

    @model_validator(mode='after')
    def check_alphanumeric(self) -> 'User':
        assert len(self.values) > 0, "values must be non-empty"
        assert len(self.values) == self.config['n_depth_pairs'], "values must be of length n_depth_pairs"

        return self

    # @model_validator(mode='after')
    # def check_alphanumeric(self) -> 'User':
    #     assert len(self.values) > 0, "values must be non-empty"
    #     print('len of values', len(self.values))
    #     print("self config", self.config)
    #     assert len(self.values) == self.config['n_depth_pairs'], "values must be of length n_depth_pairs"
    #     return self

def load_config():
    config: Dict = {}
    with open(os.path.join(WORK_DIR, "config.yaml"), "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    # print("ds config", config)
    return config

try:
    # print("123")
    # config = load_config()
    user = User(name='David', age=18, is_active=True, config=load_config())
    model_fields = user.model_fields.keys()
    import ipdb; ipdb.set_trace()
except ValidationError as exc:
    print(exc)