from pydantic import BaseModel, NonNegativeInt, constr, ConfigDict, ValidationError, model_validator, Field, validator
from typing import Optional, Tuple, Union, Dict, Any



class WalletUpdateModel(BaseModel):
    title: Optional[constr(min_length=1, max_length=40)] = Field(None, alias='wallet_title')
    balance: Optional[NonNegativeInt] = Field(None, alias='wallet_balance')
    description: Optional[constr(min_length=1)] = Field(None, alias='wallet_description')

        
    model_config = ConfigDict(extra='forbid')


class WalletCreateModel(BaseModel):
    title: Union[constr(min_length=1, max_length=40), None] = Field(alias='wallet_title')
    balance: NonNegativeInt = Field(alias='wallet_balance')
    description: Union[constr(min_length=1), None] = Field(alias='wallet_description')
    
    model_config = ConfigDict(extra='forbid')


class AccountRegistration(BaseModel):
    name: constr(min_length=4, max_length=50) = Field(alias='account_name')
    login: constr(min_length=4, max_length=25) = Field(alias='account_login')
    password: constr(min_length=4, max_length=25) = Field(alias='account_password')
    
    model_config = ConfigDict(extra='forbid')


class AccountLogin(BaseModel):
    login: constr(min_length=4, max_length=25) = Field(alias='account_login')
    password: constr(min_length=4, max_length=25) = Field(alias='account_password')
    
    model_config = ConfigDict(extra='forbid')
