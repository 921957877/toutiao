from flask_restful import Resource
from flask_limiter.util import get_remote_address
from flask import request, current_app, g
from flask_restful.reqparse import RequestParser
import random
from datetime import datetime, timedelta
from redis.exceptions import ConnectionError
from celery_tasks.sms.tasks import send_verification_code
from . import constants
from utils import parser
from models import db
from models.user import User, UserProfile
from utils.jwt_util import generate_jwt
from utils.limiter import limiter as lmt
from utils.decorators import set_db_to_read, set_db_to_write, login_required


class SMSVerificationCodeResource(Resource):
    """
    短信验证码
    """
    error_message = 'Too many requests.'

    decorators = [
        lmt.limit(constants.LIMIT_SMS_VERIFICATION_CODE_BY_MOBILE,
                  key_func=lambda: request.view_args['mobile'],
                  error_message=error_message),
        lmt.limit(constants.LIMIT_SMS_VERIFICATION_CODE_BY_IP,
                  key_func=get_remote_address,
                  error_message=error_message)
    ]

    def get(self, mobile):
        code = '{:0>6d}'.format(random.randint(0, 999999))
        current_app.redis_master.setex('app:code:{}'.format(mobile), constants.SMS_VERIFICATION_CODE_EXPIRES, code)
        send_verification_code.delay(mobile, code)
        return {'mobile': mobile}


class AuthorizationResource(Resource):
    """
    认证
    """
    method_decorators = {
        'post': [set_db_to_write],
        'put': [set_db_to_read],
        'get': [login_required]
    }

    def _generate_tokens(self, user_id, with_refresh_token=True):
        """
        生成访问令牌和刷新令牌
        :param user_id: 用户id
        :return: 访问令牌和刷新令牌
        """
        # 生成访问令牌
        payload = {
            'user_id': user_id,
            'is_refresh': False
        }
        expiry = datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRY_HOURS'])
        access_token = generate_jwt(payload, expiry)
        # 生成刷新令牌
        if with_refresh_token:
            payload = {
                'user_id': user_id,
                'is_refresh': True
            }
            expiry = datetime.utcnow() + timedelta(days=current_app.config['JWT_REFRESH_DAYS'])
            refresh_token = generate_jwt(payload, expiry)
        else:
            refresh_token = None
        return access_token, refresh_token

    # def _generate_tokens(self, user_id, with_refresh_token=True):
    #     """
    #     生成token 和refresh_token
    #     :param user_id: 用户id
    #     :return: token, refresh_token
    #     """
    #     # 颁发JWT
    #     pass

    def post(self):
        """
        登录创建token
        """
        json_parser = RequestParser()
        json_parser.add_argument('mobile', type=parser.mobile, required=True, location='json')
        json_parser.add_argument('code', type=parser.regex(r'^\d{6}$'), required=True, location='json')
        args = json_parser.parse_args()
        mobile = args.mobile
        code = args.code

        # 从redis中获取验证码
        key = 'app:code:{}'.format(mobile)
        try:
            real_code = current_app.redis_master.get(key)
        except ConnectionError as e:
            current_app.logger.error(e)
            real_code = current_app.redis_slave.get(key)

        try:
            current_app.redis_master.delete(key)
        except ConnectionError as e:
            current_app.logger.error(e)

        if not real_code or real_code.decode() != code:
            return {'message': 'Invalid code.'}, 400

        # 查询或保存用户
        user = User.query.filter_by(mobile=mobile).first()

        if user is None:
            # 用户不存在，注册用户
            user_id = current_app.id_worker.get_id()
            user = User(id=user_id, mobile=mobile, name=mobile, last_login=datetime.now())
            db.session.add(user)
            profile = UserProfile(id=user.id)
            db.session.add(profile)
            db.session.commit()
        else:
            if user.status == User.STATUS.DISABLE:
                return {'message': 'Invalid user.'}, 403

        token, refresh_token = self._generate_tokens(user.id)

        return {'token': token, 'refresh_token': refresh_token}, 201

    def get(self):
        return {'message': 'OK', 'user_id': g.user_id, 'is_refresh': g.is_refresh}

    def put(self):
        """校验刷新令牌并生成新的访问令牌"""
        # 如果可以取出用户信息并且发送的是刷新令牌
        if g.user_id and g.is_refresh:
            # 生成新的访问令牌并返回
            access_token, refresh_token = self._generate_tokens(g.user_id, with_refresh_token=False)
            return {'token': access_token}, 201
        else:
            return {'message': 'Invalid refresh token'}, 401
