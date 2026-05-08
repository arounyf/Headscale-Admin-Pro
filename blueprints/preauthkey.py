import requests
from datetime import datetime, timedelta
from flask_login import current_user, login_required
from flask import Blueprint, request,current_app
from exts import SqliteDB
from utils import table_res, res, to_request, is_user_mode
import json
from datetime import datetime

bp = Blueprint("preauthkey", __name__, url_prefix='/api/preauthkey')




@bp.route('/getPreAuthKey')
@login_required
def getPreAuthKey():
    # 调用 Headscale API 获取所有预共享密钥
    url = '/api/v1/preauthkey'
    response = to_request('GET', url)

    # 校验 API 响应是否成功
    if response['code'] != '0':
        return res(response['code'], response['msg'])

    # 解析 API 返回数据
    api_data = json.loads(response['data'])
    all_pre_auth_keys = api_data.get('preAuthKeys', [])

    # 按角色过滤数据
    filtered_keys = []
    for key in all_pre_auth_keys:
        if current_user.role != 'manager' or is_user_mode():
            if int(key['user']['id']) == current_user.id:
                filtered_keys.append(key)
        else:
            filtered_keys.append(key)

    # 计算总记录数
    total_count = len(filtered_keys)

    # 取消分页，直接使用所有数据
    paginated_keys = filtered_keys

    # 数据格式化
    pre_auth_keys_list = []
    for key in paginated_keys:
        # 处理创建时间
        created_at_utc = datetime.fromisoformat(key['createdAt'].replace('Z', '+00:00'))
        created_at_local = created_at_utc.astimezone()
        create_time = created_at_local.strftime('%Y-%m-%d %H:%M:%S')

        # 处理过期时间
        expiration = ''
        if key['expiration']:
            expiration_utc = datetime.fromisoformat(key['expiration'].replace('Z', '+00:00'))
            expiration_local = expiration_utc.astimezone()
            expiration = expiration_local.strftime('%Y-%m-%d %H:%M:%S')

        pre_auth_keys_list.append({
            'id': key['id'],
            'key': key['key'],
            'name': key['user']['name'],
            'create_time': create_time,
            'expiration': expiration,
            'reusable': key.get('reusable', False),
            'ephemeral': key.get('ephemeral', False)
        })

    return table_res('0','获取成功', pre_auth_keys_list, total_count, len(pre_auth_keys_list))




@bp.route('/addKey', methods=['GET','POST'])
@login_required
def addKey():

    reusable = request.form.get('reusable', 'true').lower() in ('true', '1', 'on')
    ephemeral = request.form.get('ephemeral', 'false').lower() in ('true', '1', 'on')
    expire_days = request.form.get('expireDays', '7')

    try:
        expire_days = int(expire_days)
    except (ValueError, TypeError):
        expire_days = 7

    expire_date = datetime.now() + timedelta(days=expire_days)

    url = '/api/v1/preauthkey'
    data = {
        'user': current_user.id,
        'reusable': reusable,
        'ephemeral': ephemeral,
        'expiration': expire_date.isoformat() + 'Z'
    }

    response = to_request('POST', url, data)

    if response['code'] == '0':
        return res('0', '获取成功', response['data'])
    else:
        return res(response['code'], response['msg'])




@bp.route('/delKey', methods=['GET','POST'])
@login_required
def delKey():
    key_id = request.form.get('keyId')
    try:
        with SqliteDB() as cursor:
            user_id = cursor.execute("SELECT user_id FROM pre_auth_keys WHERE id =? ", (key_id,)).fetchone()[0]
            print(user_id)
            if user_id == current_user.id or current_user.role == 'manager':
                cursor.execute("DELETE FROM pre_auth_keys WHERE id =?", (key_id,))
                return res('0', '删除成功')
            else:
                return res('1', '非法请求')
    except Exception as e:
        print(f"发生未知错误: {e}")
        return res('1', '删除失败')

