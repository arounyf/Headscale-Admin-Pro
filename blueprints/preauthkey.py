import requests
from datetime import datetime, timedelta, timezone
from flask_login import current_user, login_required
from flask import Blueprint, request,current_app
from exts import SqliteDB
from utils import table_res, res, to_request, is_user_mode, api_ts
import json

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
        # tagged keys 的 user 为 null，只对管理员可见
        if key.get('user') is None:
            continue
        if current_user.role != 'manager' or is_user_mode():
            if int(key['user']['id']) != current_user.id:
                continue
        filtered_keys.append(key)

    # 计算总记录数
    total_count = len(filtered_keys)

    # 取消分页，直接使用所有数据
    paginated_keys = filtered_keys

    # 数据格式化
    pre_auth_keys_list = []
    for key in paginated_keys:
        # createdAt / expiration 是 API 给的绝对时刻，走 api_ts 转成和 display_ts
        # 同一套的北京墙钟。以前这里手写 fromisoformat + 不带参数的 .astimezone()
        # （取容器时区）—— 显示时区就成了容器的隐式属性，换个 TZ 环境就跟别页对不上。
        # expiration 为空时 api_ts 返回 ''。
        create_time = api_ts(key['createdAt'])
        expiration = api_ts(key['expiration'])

        user = key.get('user') or {}
        pre_auth_keys_list.append({
            'id': key['id'],
            'key': key['key'],
            'name': user.get('name', '-'),
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

    # 这是跨 API 边界发出去的值，必须是真 UTC。原来是 `datetime.now()`（容器本地）
    # 直接拼一个 'Z' —— 等于把本地时间谎报成 UTC，操作者填 7 天，密钥实际活
    # 7 天 8 小时，比设定期限长。
    expire_date = datetime.now(timezone.utc) + timedelta(days=expire_days)

    url = '/api/v1/preauthkey'
    data = {
        'user': current_user.id,
        'reusable': reusable,
        'ephemeral': ephemeral,
        'expiration': expire_date.isoformat().replace('+00:00', 'Z')
    }

    response = to_request('POST', url, data)

    if response['code'] == '0':
        return res('0', '获取成功', response['data'])
    else:
        return res(response['code'], response['msg'])




@bp.route('/delKey', methods=['GET','POST'])
@login_required
def delKey():
    """删除预授权密钥，由 headscale 执行。

    以前是这里直接 DELETE FROM pre_auth_keys。表和 headscale 共用，删掉
    它确实也能看到，但绕过 API 意味着 headscale 自己的校验和后续清理都
    不会发生 —— delUser 当初也是这么改成走 API 的。
    """
    key_id = request.form.get('keyId')

    with SqliteDB() as cursor:
        row = cursor.execute("SELECT user_id FROM pre_auth_keys WHERE id =?", (key_id,)).fetchone()

    if not row:
        return res('1', '密钥不存在')

    if row[0] != current_user.id and current_user.role != 'manager':
        return res('1', '非法请求')

    # DeletePreAuthKey 是无 body 的 DELETE，grpc-gateway 把 id 映射成 query 参数
    response = to_request('DELETE', f'/api/v1/preauthkey?id={key_id}')
    if response['code'] == '0':
        return res('0', '删除成功')

    return res('1', f"删除失败：{response['msg']}")

