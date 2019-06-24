import random


# 多态的实现步骤：
# 1.子类继承父类
# 2.在父类中定义公共方法或公共属性
# 3.在子类中重写父类的公共方法或公共属性实现"多态"
class CacheTTLBase:
    """缓存过期时间基类"""
    cache_TTL = 0  # 缓存的过期时间
    random_TTL = 0  # 为了防止缓存雪崩问题而添加的随机过期时间

    @classmethod
    def get_value(cls):
        return cls.cache_TTL + random.randrange(0, cls.random_TTL)


class UserCacheTTL(CacheTTLBase):
    """用户缓存数据的过期时间"""
    cache_TTL = 60 * 60 * 2
    random_TTL = 60 * 10


class DefaultCacheTTL(CacheTTLBase):
    """默认值缓存的过期时间"""
    cache_TTL = 60 * 10
    random_TTL = 60
