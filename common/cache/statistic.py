# 完成统计类数据的持久化存储
from flask import current_app
from redis import RedisError
from redis import StrictRedis
from sqlalchemy import func
from models import db
from models.news import Article
from models.user import Relation


class CountStorageBase:
    """数量统计基类"""

    key = 'count:user'

    @classmethod
    def get(cls, user_id):
        """
        获取用户发布的文章数量
        :param user_id: 指定用户id
        :return: 该用户发布的文章数量
        """
        # 直接从redis中取数据(mysql中不再存储统计相关的冗余字段)
        r = current_app.redis_master  # type:StrictRedis
        try:
            # 从redis主机获取数据
            articles_count = r.zscore(cls.key, user_id)
        except RedisError as e:
            current_app.logger.error(e)
            # 如果从redis主机中取不出数据，则从redis从机中取数据
            articles_count = current_app.redis_slave.zscore(cls.key, user_id)
        if articles_count:
            return int(articles_count)  # 从redis中取出来的是bytes，需要转成int类型
        else:
            return 0  # 如果从redis中取不出数据也不会报错，而是返回null，由于这里是发布文章数量，所以需要返回0

    @classmethod
    def incr(cls, user_id):
        """
        增加指定用户的文章发布数量
        :param user_id: 指定用户id
        """
        r = current_app.redis_master  # type: StrictRedis
        try:
            r.zincrby(cls.key, user_id)
        except RedisError as e:
            current_app.logger.error(e)

    @classmethod
    def reset(cls, ret):
        # 创建事务管道
        r = current_app.redis_master  # type: StrictRedis
        pl = r.pipeline()
        # 删除redis中保存的所有用户文章发布数量数据
        pl.delete(cls.key)
        # 将从mysql数据库中获取的所有用户文章发布数量添加到redis中
        for user_id, article_count in ret:
            pl.zadd(cls.key, article_count, user_id)
        # 执行管道处理
        pl.execute()


class UserArticleCountStorage(CountStorageBase):
    """用户文章发布数量统计类"""
    key = 'count:user:arts'

    @classmethod
    def db_query(cls):
        # 从mysql数据库中查询所有用户文章发布数量
        ret = db.session.query(Article.user_id, func.count(Article.id)).filter(
            Article.status == Article.STATUS.APPROVED).group_by(
            Article.user_id).all()
        return ret


class UserFollowingCountStorage(CountStorageBase):
    """用户关注数量统计类"""
    key = 'count:user:following'

    @classmethod
    def db_query(cls):
        # 从mysql数据库中查询所有用户文章发布数量
        ret = db.session.query(Relation.user_id, func.count(Relation.target_user_id)).filter(
            Relation.relation == Relation.RELATION.FOLLOW).group_by(
            Relation.user_id).all()
        return ret


class UserFansCountStorage(CountStorageBase):
    """用户粉丝数量统计类"""
    key = 'count:user:fans'

    @classmethod
    def db_query(cls):
        # 从mysql数据库中查询所有用户文章发布数量
        ret = db.session.query(Relation.target_user_id, func.count(Relation.user_id)).filter(
            Relation.relation == Relation.RELATION.FOLLOW).group_by(
            Relation.target_user_id).all()
        return ret
