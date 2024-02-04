from datetime import datetime, timedelta

import jwt

from functools import wraps
from flask import request, jsonify, make_response
from flask.blueprints import Blueprint
from werkzeug.security import generate_password_hash, check_password_hash

from database import database_api
from config import SECRET_KEY

api_v1 = Blueprint("api", __name__, url_prefix="/api/v1")


def token_required(api_function):
    @wraps(api_function)
    def decorated(*args, **kwargs):
        authorization_header = request.headers.get('Authorization')
        if not authorization_header:
            return jsonify({"message": 'Authentication failed!'})
        auth_type, jwt_token = authorization_header.split(' ')
        try:
            data = jwt.decode(jwt=jwt_token, key=SECRET_KEY, algorithms=["HS256"])
            account_id = data['id']
            return api_function(account_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": 'Timeout data!'})
        except jwt.InvalidTokenError:
            return jsonify({"message": 'Incorrect authentication data!'})
    return decorated


@api_v1.route('/testing/', methods=['GET'])
@token_required
def testing_api(account_id):
    account = database_api.get_account_by_id(account_id)
    response = make_response(jsonify({"account_id": account_id, 'account_name': account['account_name']}), 200)
    return response


@api_v1.route('/auth/login/', methods=['POST'])
def auth_login_new_account():
    data = request.get_json()
    name = data.get('account_name')
    login = data.get('account_login')
    password = data.get('account_password')
    hash_password = generate_password_hash(password)
    account_id = database_api.login_new_account(name, login, hash_password)
    if account_id:
        encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': datetime.utcnow() + timedelta(days=7)}, key=SECRET_KEY, algorithm="HS256")
        response = make_response(jsonify({"message": 'Account was created!'}), 200)
        response.headers['Authorization'] = 'Bearer ' + encoded_jwt
        print('AccountToken:' + encoded_jwt, f'Длина:{len(encoded_jwt)}')
        return response
    return make_response(jsonify({"message": 'Bad data!'}), 404)

@api_v1.route('/auth/login/refresh', methods=['POST'])
def auth_login_refresh():
    data = request.get_json()
    login = data.get('account_login')
    password = data.get('account_password')
    account = database_api.get_account_by_login(login)
    if not account:
        return jsonify({"message": 'Bad data!'})
    if not check_password_hash(account.get('account_password'), password):
        return jsonify({"message": 'Bad data!'})
    account_id = account.get('account_id')
    encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': datetime.utcnow() + timedelta(days=7)}, key=SECRET_KEY, algorithm="HS256")
    response = make_response(jsonify({"message": 'Successful authentication!'}), 200)
    response.headers['Authorization'] = 'Bearer ' + encoded_jwt
    return response
    

@api_v1.route('/auth/logout/', methods=['POST'])
@token_required
def logout_account(account_id):
    encoded_jwt = jwt.encode(payload={"id": account_id, 'exp': datetime.utcnow()}, key=SECRET_KEY, algorithm="HS256")
    response = make_response(jsonify({"message": 'Successful logout!'}), 200)
    response.headers['Authorization'] = 'Bearer ' + encoded_jwt
    return response

