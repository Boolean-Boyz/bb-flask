import jwt
import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource

from __init__ import db
from model.fopl_user import FoplUser

fopl_auth_api = Blueprint('fopl_auth_api', __name__, url_prefix='/api/fopl')
api = Api(fopl_auth_api)

FOPL_COOKIE = 'fopl_token'


def fopl_token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(FOPL_COOKIE)
        if not token:
            return {'message': 'Login required'}, 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = FoplUser.query.get(data.get('fopl_id'))
            if not user:
                return {'message': 'Invalid token'}, 401
            g.fopl_user = user
        except jwt.ExpiredSignatureError:
            return {'message': 'Session expired, please log in again'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Invalid token'}, 401
        return func(*args, **kwargs)
    return wrapper


def _set_token_cookie(response, user):
    token = jwt.encode(
        {'fopl_id': user.id},
        current_app.config['SECRET_KEY'],
        algorithm='HS256',
    )
    is_prod = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
    if is_prod:
        response.set_cookie(FOPL_COOKIE, token, max_age=43200, secure=True,
                            httponly=True, path='/', samesite='None')
    else:
        response.set_cookie(FOPL_COOKIE, token, max_age=43200, secure=False,
                            httponly=False, path='/', samesite='Lax')


class _Register(Resource):
    def post(self):
        body     = request.get_json() or {}
        name     = (body.get('name') or '').strip()
        email    = (body.get('email') or '').strip().lower()
        password = body.get('password') or ''

        if len(name) < 2:
            return {'message': 'Name must be at least 2 characters'}, 400
        if '@' not in email or '.' not in email:
            return {'message': 'Valid email required'}, 400
        if len(password) < 8:
            return {'message': 'Password must be at least 8 characters'}, 400
        if FoplUser.query.filter_by(_email=email).first():
            return {'message': 'An account with that email already exists'}, 409

        user = FoplUser(name=name, email=email, password=password).create()
        if not user:
            return {'message': 'Registration failed, please try again'}, 500

        resp = jsonify({'message': f'Account created for {name}', 'user': user.read()})
        _set_token_cookie(resp, user)
        return resp


class _Login(Resource):
    def post(self):
        body     = request.get_json() or {}
        email    = (body.get('email') or '').strip().lower()
        password = body.get('password') or ''

        user = FoplUser.query.filter_by(_email=email).first()
        if not user or not user.is_password(password):
            return {'message': 'Invalid email or password'}, 401

        resp = jsonify({'message': f'Welcome back, {user.name}!', 'user': user.read()})
        _set_token_cookie(resp, user)
        return resp


class _Logout(Resource):
    @fopl_token_required
    def delete(self):
        resp = jsonify({'message': 'Logged out successfully'})
        resp.set_cookie(FOPL_COOKIE, '', max_age=0, path='/')
        return resp


class _Me(Resource):
    @fopl_token_required
    def get(self):
        return jsonify(g.fopl_user.read())


api.add_resource(_Register, '/register')
api.add_resource(_Login,    '/login')
api.add_resource(_Logout,   '/login')  # DELETE /login → logout
api.add_resource(_Me,       '/me')
