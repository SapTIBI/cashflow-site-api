from datetime import datetime, timedelta
from functools import wraps

import jwt
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


@api_v1.route('/testing/', methods=['GET'])
@token_required
def testing_api(account_id):
    try:
        account = database_api.get_account_by_id(account_id)
        account_name = account.get('account_name')
        return jsonify({"account_id": account_id, 'account_name': account_name}), 200
    except database_api.DatabaseError as e:
        return jsonify({"message": 'Failed on server!'}), 500


@api_v1.route('/auth/login/', methods=['POST'])
def auth_login_new_account():
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


@api_v1.route('/auth/login/refresh', methods=['POST'])
def auth_login_refresh():
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

