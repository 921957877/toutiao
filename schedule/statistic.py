from cache.statistic import UserArticleCountStorage, UserFollowingCountStorage, UserFansCountStorage


def __fix_statistic(cls):
    # 查询mysql数据库中的统计数据
    ret = cls.db_query()
    # 校正redis中的统计数据
    cls.reset(ret)


def fix_statistic(flask_app):
    """统计数据校正"""
    # 如果db在创建时没有指定对应的app，则db操作必须在视图函数/手动创建的应用上下文中
    with flask_app.app_context():
        __fix_statistic(UserArticleCountStorage)
        __fix_statistic(UserFollowingCountStorage)
        __fix_statistic(UserFansCountStorage)
