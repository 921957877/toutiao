from flask import g, current_app
from flask_restful import Resource, reqparse

from cache.statistic import UserArticleCountStorage, UserFollowingCountStorage, UserFansCountStorage
from cache.user import UserBasicCache
from models import db
from models.user import User
from utils.decorators import login_required
from utils.parser import image_file
from utils.storage import upload_data


class PhotoResource(Resource):
    """上传头像"""
    # 进行访问限制
    method_decorators = [login_required]

    def patch(self):
        # 解析参数
        parser = reqparse.RequestParser()
        parser.add_argument('photo', location='files', required=True, type=image_file)
        args = parser.parse_args()
        file = args.photo  # type: FileStorage
        # 读取出二进制数据
        bytes = file.read()
        # 上传文件到七牛云
        file_name = upload_data(bytes)
        # 将新的头像URL更新到数据库
        User.query.filter_by(id=g.user_id).update({'profile_photo': file_name})
        db.session.commit()
        # 返回头像的URL
        return {'photo_url': current_app.config['QINIU_DOMAIN'] + file_name}


class CurrentUserResource(Resource):
    method_decorators = [login_required]  # 进行访问限制

    def get(self):
        # 根据用户id查询数据
        user_cache = UserBasicCache(g.user_id)
        # 判断user_id在缓存和数据库中是否存在
        if user_cache.exist():
            # 如存在，获得字典
            user_dict = user_cache.get()
            # 将数据拼接成json并返回
            user_dict['user_id'] = g.user_id
            user_dict['article_count'] = UserArticleCountStorage.get(g.user_id)  # 统计数据通过持久化存储类来获取数据
            user_dict['following_count'] = UserFollowingCountStorage.get(g.user_id)
            user_dict['fans_count'] = UserFansCountStorage.get(g.user_id)
            return user_dict
        else:
            # 如不存在，返回报错信息
            return {'message': 'invalid user_id'}, 400
