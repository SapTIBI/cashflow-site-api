from pydantic import BaseModel, NonNegativeInt, constr, ConfigDict, ValidationError, model_validator
from typing import Optional, Tuple, Union



class WalletUpdateModel(BaseModel):
    wallet_title: Optional[constr(min_length=1, max_length=40)] = None
    wallet_balance: Optional[NonNegativeInt] = None
    wallet_description: Optional[constr(min_length=1)] = None
    model_config = ConfigDict(extra='forbid')


class WalletCreateModel(BaseModel):
    wallet_title: Union[constr(min_length=1, max_length=40), None]
    wallet_balance: NonNegativeInt
    wallet_description: Union[constr(min_length=1), None]
    model_config = ConfigDict(extra='forbid')
    