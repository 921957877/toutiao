
from flask import g, current_app
from functools import wraps
from sqlalchemy.orm import load_only
from sqlalchemy.exc import SQLAlchemyError

from models import db


def set_db_to_read(func):
    """
    设置使用读数据库
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_read()
        return func(*args, **kwargs)

    return wrapper


def set_db_to_write(func):
    """
    设置使用写数据库
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_write()
        return func(*args, **kwargs)

    return wrapper


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 判断是否能取出user_id且携带的是访问令牌
        if g.user_id and not g.is_refresh:
            return f(*args, **kwargs)
        else:
            return {'message': 'Invalid token'}, 401
    return wrapper
