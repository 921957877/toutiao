from flask import current_app
from qiniu import Auth, put_data


def upload_data(data):
    """
    上传文件到七牛云
    :param data: 上传的二进制数据
    :return: 文件的访问url
    """
    # 需要填写你的 Access Key 和 Secret Key
    access_key = current_app.config['QINIU_ACCESS_KEY']
    secret_key = current_app.config['QINIU_SECRET_KEY']
    # 构建鉴权对象
    q = Auth(access_key, secret_key)
    # 要上传的空间
    bucket_name = current_app.config['QINIU_BUCKET_NAME']
    # 上传后保存的文件名(如果设置为None,就会生成一个随机的名称)
    key = None
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600 * 1000)
    # 上传文件
    ret, info = put_data(token, key, data)
    return ret.get('key')


if __name__ == '__main__':
    with open('1604_5069669_643471.jpg', 'rb') as f:
        data = f.read()
        file_name = upload_data(data)
        print(file_name)
