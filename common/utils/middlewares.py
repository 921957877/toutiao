from flask import request, g

from utils.jwt_util import verify_jwt


def jwt_authentication():
    """提取jwt并进行校验"""
    g.user_id = None
    g.is_refresh = False
    # 提取jwt
    header = request.headers.get('Authorization')
    if header and header.startswith('Bearer '):
        # 截取出token
        jwt_token = header[7:]
        # 校验令牌
        payload = verify_jwt(jwt_token)
        if payload:
            g.user_id = payload.get('user_id')
            g.is_refresh = payload.get('is_refresh')

