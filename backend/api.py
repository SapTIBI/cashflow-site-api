from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import request, jsonify
from flask.blueprints import Blueprint


from database import database_api
from utils import WalletUpdateModel, WalletCreateModel, AccountRegistration, AccountLogin
from config import SECRET_KEY


api_v1 = Blueprint("api", __name__, url_prefix="/api/v1")


class APIResponse:
    @staticmethod
    def success(status_code=200, message=None, data=None, headers=None):
        response_data = {
            "data": data,
            "message": message
        }
        return jsonify(response_data), status_code, headers

    @staticmethod
    def error(message, status_code=400, headers=None):
        response_data = {
            "message": message
        }
        return jsonify(response_data), status_code, headers



def token_required(api_function):
    @wraps(api_function)
    def decorated(*args, **kwargs):
        authorization_header = request.headers.get('Authorization')
        if not authorization_header:
            return APIResponse.error(message='Authentication failed', status_code=401)
        try:
            auth_type, jwt_token = authorization_header.split(' ')
            data = jwt.decode(jwt=jwt_token, key=SECRET_KEY, algorithms=["HS256"])
            account_id = data['id']
            return api_function(account_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return APIResponse.error(message='Token has expired', status_code=401)
        except jwt.InvalidTokenError:
            return APIResponse.error(message='Invalid token', status_code=401)
    return decorated


@api_v1.before_request
def before_request():
    if request.method == 'POST' or request.method == 'PUT':
        if not request.is_json:
            return APIResponse.error(message='Unsupported Media Type', status_code=415)
        
        
@api_v1.errorhandler(400)
def handle_bad_request(error):
    return APIResponse.error(message='Bad request', status_code=400)


@api_v1.route('/testing/', methods=['GET'])
@token_required
def testing_api(account_id):
    try:
        account = database_api.get_account_by_id(account_id)
        account_name = account.get('account_name')
        return jsonify({"account_id": account_id, 'account_name': account_name}), 200 # -> return APIResponse.success
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    except Exception as e:
        return APIResponse.error(message='Unexpected error on server', status_code=500)


@api_v1.route('/auth/registration/', methods=['POST'])
def auth_registration():
    data = request.get_json()
    try:
        validated_data = AccountRegistration(**data).model_dump()
    except ValueError as e:
        return APIResponse.error(message='Bad data', status_code=400)
    try:
        account = database_api.login_new_account(validated_data)
    except database_api.DuplicatedInformationError as e:
        return APIResponse.error(message='Account with this login already exist', status_code=409)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed while creating account', status_code=409)
    try:
        account_id = account.get('account_id')
        expiration_time = datetime.utcnow() + timedelta(days=7)
        encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
        headers = {'Authorization': 'Bearer ' + encoded_jwt}
        return APIResponse.success(message='Account was created', data=account, headers=headers, status_code=201)
    except Exception as e:
        return APIResponse.error(message='Failed on server', status_code=500)


@api_v1.route('/auth/login/', methods=['POST'])
def auth_login():
    data = request.get_json()
    try:
        validated_data = AccountLogin(**data).model_dump()
    except ValueError as e:
        return APIResponse.error(message='Bad data', status_code=400)
    try:
       account = database_api.get_account_by_credentials(validated_data)
    except database_api.IncorrectCredentialsError as e:
        return APIResponse.error(message='Wrong login or password', status_code=401)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    try:
        account_id = account.get('account_id')
        expiration_time = datetime.utcnow() + timedelta(days=7)
        encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
        headers = {'Authorization': 'Bearer ' + encoded_jwt}
        del account['account_id']
        return APIResponse.success(message='Successful authentication', data=account, headers=headers, status_code=200)
    except Exception as e:
        return APIResponse.error(message='Failed on server', status_code=500)

@api_v1.route('/auth/logout/', methods=['POST'])
@token_required
def logout_account(account_id):
    try:
        expiration_time = datetime.utcnow()
        encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
        headers = {'Authorization': 'Bearer ' + encoded_jwt}
        return APIResponse.success(message='Successful logout', data=None, headers=headers, status_code=200)
    except Exception as e:
        return APIResponse.error(message='Failed on server', status_code=500)

@api_v1.route('/account/wallets/', methods=['POST'])
@token_required
def create_wallet_account(account_id):
    data = request.get_json()
    try:
        validated_data = WalletCreateModel(**data).model_dump(exclude_unset=True)
    except ValueError as e:
        return APIResponse.error(message='Bad data', status_code=400)
    try:
        created_wallet : dict = database_api.create_wallet_account(account_id=account_id, data=validated_data)                                         
        return APIResponse.success(message='Wallet was created', data=created_wallet, status_code=201)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    except Exception as e:
        return APIResponse.error(message='Unexpected error on server', status_code=500)


@api_v1.route('/account/wallets/<int:wallet_id>', methods=['DELETE'])
@token_required
def delete_wallet_account(account_id, wallet_id):
    try:
        is_wallet_found = database_api.delete_wallet_account(account_id, wallet_id)
        if not is_wallet_found:
            return APIResponse.error(message='No wallet found for deletion', status_code=404)
        return APIResponse.success(status_code=204)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    except Exception as e:
        return APIResponse.error(message='Unexpected error on server', status_code=500)
    

@api_v1.route('/account/wallets/<int:wallet_id>', methods=['PATCH'])
@token_required
def update_wallet_account(account_id, wallet_id):
    data = request.get_json()
    if not data:
        return APIResponse.error(message='At least one field is required for update', status_code=400)
    try:
        validated_data = WalletUpdateModel(**data).model_dump(exclude_unset=True)
    except ValueError as e:
        return APIResponse.error(message='Bad data', status_code=400)
    try:
        print(validated_data)
        updated_wallet = database_api.update_wallet_account(account_id, wallet_id, validated_data)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    if not updated_wallet:
        return APIResponse.error(message='No wallet found', status_code=404)
    return APIResponse.success(message='Wallet finded successfully', data=updated_wallet, status_code=200)
 

@api_v1.route('/account/wallets/<int:wallet_id>', methods=['GET'])
@token_required
def get_wallet_account(account_id, wallet_id):
    try:
        wallet_data = database_api.get_wallet_account(account_id, wallet_id)
        if not wallet_data:
            return APIResponse.error(message='No wallet found', status_code=404)
        return APIResponse.success(message='Wallet finded successfully', data=wallet_data, status_code=200)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    except Exception as e:
        return APIResponse.error(message='Unexpected error on server', status_code=500)

@api_v1.route('/account/wallets/', methods=['GET'])
@token_required
def get_wallets_account(account_id):
    try:
        wallets_data = database_api.get_wallets_account(account_id)
        if not wallets_data:
            return APIResponse.error(message='No wallets found', status_code=404)
        return APIResponse.success(message='Wallets finded successfully', data=wallets_data, status_code=200)
    except database_api.DatabaseError as e:
        return APIResponse.error(message='Failed on server', status_code=500)
    except Exception as e:
        return APIResponse.error(message='Unexpected error on server', status_code=500)