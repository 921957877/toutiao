"""
面向对象思想：将具有相同特征和行为的事物看做整体
用户基本信息缓存类
属性：用户id
方法：获取缓存，删除缓存
"""
import pickle
from flask import current_app
from redis import RedisError
from rediscluster import StrictRedisCluster
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import load_only
from cache.constants import UserCacheTTL, DefaultCacheTTL
from models.user import User


class UserBasicCache:
    """用户基本数据缓存类"""
    def __init__(self, user_id):
        self.user_id = user_id  # 用户id
        self.key = 'user:{}:basic'.format(self.user_id)  # redis中字符串(存储用户基本信息)的键

    def save(self):
        """
        查询数据库中的数据并保存到redis缓存中
        :return: 如有，返回data_dict字典，如没有，返回None
        """
        r = current_app.redis_cluster  # type: StrictRedisCluster
        try:
            # 如没有数据，向数据库进行查询
            user = User.query.options(
                load_only(User.mobile, User.name, User.profile_photo, User.introduction,
                          User.certificate)).filter_by(
                id=self.user_id).first()
        except DatabaseError as e:
            current_app.logger.error(e)
            raise e  # 将操作的决策权交给消费者
        # 判断数据库中是否有数据
        if user:
            # 如有，将数据写入缓存并返回
            data_dict = {
                'mobile': user.mobile,
                'name': user.name,
                'profile_photo': user.profile_photo,
                'introduction': user.introduction,
                'certificate': user.certificate
            }
            data_string = pickle.dumps(data_dict)
            try:
                r.setex(self.key, UserCacheTTL.get_value(), data_string)
            except RedisError as e:
                current_app.logger.error(e)
            return data_dict
        # 如没有，将默认值-1写入缓存并返回None
        else:
            try:
                r.setex(self.key, DefaultCacheTTL.get_value(), -1)
            except RedisError as e:
                current_app.logger.error(e)
            return None

    def get(self):
        """获取缓存"""
        r = current_app.redis_cluster  # type: StrictRedisCluster
        try:
            # 从缓存中读取数据
            cache_data = r.get(self.key)
        except RedisError as e:
            # 记录到日志里
            current_app.logger.error(e)
            cache_data = None
        # 判断缓存中是否有数据
        if cache_data:
            # 判断数据是否是默认值-1
            if cache_data == b'-1':  # 说明数据库中没有该数据
                return None
            # 如有,直接返回
            cache_dict = pickle.loads(cache_data)
            return cache_dict
        else:
            self.save()

    def clear(self):
        """删除缓存"""
        r = current_app.redis_cluster  # type: StrictRedisCluster
        try:
            r.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

    def exist(self):
        """判断前端传来的数据在redis缓存和数据库中是否存在"""
        r = current_app.redis_cluster  # type: StrictRedisCluster
        try:
            # 从缓存中读取数据
            cache_data = r.get(self.key)
        except RedisError as e:
            # 记录到日志里
            current_app.logger.error(e)
            cache_data = None
        # 判断缓存中是否有数据
        if cache_data:
            # 判断数据是否是默认值-1
            if cache_data == b'-1':  # 说明数据库中没有该数据
                return False
            # 如Redis缓存中有,返回True
            return True
        else:
            # 如缓存中没有数据，则从数据库中查询数据
            data_dict = self.save()
            # 如数据库中有数据,返回True
            if data_dict:
                return True
            else:
                # 如数据库中也查询不到数据，返回False
                return False
