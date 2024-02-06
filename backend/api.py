from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import request, jsonify
from flask.blueprints import Blueprint
from werkzeug.security import generate_password_hash, check_password_hash

from database import database_api
from utils import WalletUpdateModel, WalletCreateModel
from config import SECRET_KEY


api_v1 = Blueprint("api", __name__, url_prefix="/api/v1")


def token_required(api_function):
    @wraps(api_function)
    def decorated(*args, **kwargs):
        authorization_header = request.headers.get('Authorization')
        if not authorization_header:
            return jsonify({"message": 'Authentication failed!'}), 401
        try:
            auth_type, jwt_token = authorization_header.split(' ')
            data = jwt.decode(jwt=jwt_token, key=SECRET_KEY, algorithms=["HS256"])
            account_id = data['id']
            return api_function(account_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": 'Token has expired'}), 401   
        except jwt.InvalidTokenError:
            return jsonify({"message": 'Invalid token'}), 401
    return decorated


@api_v1.before_request
def before_request():
    if request.method == 'POST' or request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Unsupported Media Type"}), 415
        
        
@api_v1.errorhandler(400)
def handle_bad_request(error):
    return jsonify({"message": "Bad request"}), 400


@api_v1.route('/testing/', methods=['GET'])
@token_required
def testing_api(account_id):
    try:
        account = database_api.get_account_by_id(account_id)
        account_name = account.get('account_name')
        return jsonify({"account_id": account_id, 'account_name': account_name}), 200
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    except Exception as e:
        return jsonify({"message": 'Unexpected error on server!'}), 500


@api_v1.route('/auth/registration/', methods=['POST'])
def auth_registration():
    data = request.get_json()
    name = data.get('account_name')
    login = data.get('account_login')
    password = data.get('account_password')
    if not all((name, login, password)):
        return jsonify({"message": 'Bad data!'}), 400
    hash_password = generate_password_hash(password)
    try:
        account_id = database_api.login_new_account(name, login, hash_password)
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    if account_id:
        expiration_time = datetime.utcnow() + timedelta(days=7)
        encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
        response = jsonify({"message": 'Account was created!'})
        response.headers['Authorization'] = 'Bearer ' + encoded_jwt
        return response, 201
    return jsonify({"message": 'Failed to create account!'}), 409


@api_v1.route('/auth/login/', methods=['POST'])
def auth_login():
    data = request.get_json()
    login = data.get('account_login')
    password = data.get('account_password')
    if not all((login, password)):
        return jsonify({"message": 'Bad data!'}), 400
    try:
       account = database_api.get_account_by_login(login) 
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    if not account or not check_password_hash(account.get('account_password'), password):
        return jsonify({"message": 'Bad data!'}), 400
    account_id = account.get('account_id')
    if not account_id:
        return jsonify({"message": 'Bad data!'}), 400
    expiration_time = datetime.utcnow() + timedelta(days=7)
    encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
    response = jsonify({"message": 'Successful authentication!'})
    response.headers['Authorization'] = 'Bearer ' + encoded_jwt
    return response, 200
    

@api_v1.route('/auth/logout/', methods=['POST'])
@token_required
def logout_account(account_id):
    expiration_time = datetime.utcnow()
    encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': expiration_time}, key=SECRET_KEY, algorithm="HS256")
    response = jsonify({"message": 'Successful logout!'})
    response.headers['Authorization'] = 'Bearer ' + encoded_jwt
    return response, 200


@api_v1.route('/account/wallets/', methods=['POST'])
@token_required
def create_wallet_account(account_id):
    data = request.get_json()
    try:
        validated_data = WalletCreateModel(**data).model_dump(exclude_unset=True)
    except ValueError as e:
        return jsonify({"message": 'Bad data!'}), 400
    try:
        mapping_db = {
            "wallet_title": "title",
            "wallet_description": "description",
            "wallet_balance": "balance"
        }
        mapped_data = {mapping_db[key]:value for key, value in validated_data.items()}
        created_wallet : dict = database_api.create_wallet_account(account_id=account_id, data=mapped_data)                                         
        response_data = {
            'message': 'Wallet was created!',
            'data': created_wallet
        }
        return jsonify(response_data), 201
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    except Exception as e:
        return jsonify({"message": 'Unexpected error on server!'}), 500


@api_v1.route('/account/wallets/<int:wallet_id>', methods=['DELETE'])
@token_required
def delete_wallet_account(account_id, wallet_id):
    try:
        is_wallet_found = database_api.delete_wallet_account(account_id, wallet_id)
        if not is_wallet_found:
            return jsonify({"message": "No wallet found for deletion!"}), 404
        return jsonify({"message": "Wallet deleted successfully!"}), 200
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    except Exception as e:
        return jsonify({"message": 'Unexpected error on server!'}), 500
    

@api_v1.route('/account/wallets/<int:wallet_id>', methods=['PATCH'])
@token_required
def update_wallet_account(account_id, wallet_id):
    data = request.get_json()
    try:
        validated_data = WalletUpdateModel(**data).model_dump(exclude_unset=True)
    except ValueError as e:
        return jsonify({"message": 'Bad data!'}), 400
    if not validated_data:
        return jsonify({"message": "At least one field is required for update"}), 400
    mapping_db = {
        "wallet_title": "title",
        "wallet_description": "description",
        "wallet_balance": "balance"
    }
    mapped_data = {mapping_db[key]:value for key, value in validated_data.items()}
    try:
        updated_wallet = database_api.update_wallet_account(account_id, wallet_id, mapped_data)
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    if not updated_wallet:
        return jsonify({'message': 'No wallet found!'}), 404
    wallet_id = updated_wallet.get('wallet_id')
    wallet_balance = updated_wallet.get('wallet_balance')
    wallet_title = updated_wallet.get('wallet_title')
    wallet_description = updated_wallet.get('wallet_description')
    response_data = {
            'message': 'Wallet finded successfully!',
            'data': {
                'wallet_id:': wallet_id,
                'wallet_balance': wallet_balance,
                'wallet_title': wallet_title,
                'wallet_description': wallet_description,
            }
        }
    return jsonify(response_data), 200


@api_v1.route('/account/wallets/<int:wallet_id>', methods=['GET'])
@token_required
def get_wallet_account(account_id, wallet_id):
    try:
        wallet_data = database_api.get_wallet_account(account_id, wallet_id)
        if not wallet_data:
            return jsonify({'message': 'No wallet found!'}), 404
        response_data = {
            'message': 'Wallet finded successfully!',
            'data': wallet_data
        }
        return jsonify(response_data), 200
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500
    except Exception as e:
        return jsonify({"message": 'Unexpected error on server!'}), 500