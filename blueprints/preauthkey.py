import requests
from datetime import datetime, timedelta
from flask_login import current_user, login_required
from flask import Blueprint, request,current_app
from exts import SqliteDB
from utils import table_res, res, to_request

bp = Blueprint("preauthkey", __name__, url_prefix='/api/preauthkey')



@bp.route('/getPreAuthKey')
@login_required
def getPreAuthKey():
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        # 构建基础查询语句
        base_query = """
            SELECT 
                pre_auth_keys.id,
                pre_auth_keys.key,
                users.name,
                strftime('%Y-%m-%d %H:%M:%S', pre_auth_keys.created_at, 'localtime') as created_at,
                strftime('%Y-%m-%d %H:%M:%S', pre_auth_keys.expiration, 'localtime') as expiration
            FROM 
                pre_auth_keys
            JOIN 
                users ON pre_auth_keys.user_id = users.id
        """

        # 判断用户角色
        if current_user.role != 'manager':
            base_query += " WHERE pre_auth_keys.user_id =? "
            params = (current_user.id,)
        else:
            params = ()

        # 查询总记录数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']

        # 分页查询
        paginated_query = f"{base_query} LIMIT? OFFSET? "
        paginated_params = params + (per_page, offset)
        cursor.execute(paginated_query, paginated_params)
        pre_auth_keys = cursor.fetchall()

    # 数据格式化
    pre_auth_keys_list = []
    for pre_auth_key in pre_auth_keys:
        pre_auth_keys_list.append({
            'id': pre_auth_key['id'],
            'key': pre_auth_key['key'],
            'name': pre_auth_key['name'],
            'create_time': pre_auth_key['created_at'],
            'expiration': pre_auth_key['expiration']
        })



    return table_res('0','获取成功',pre_auth_keys_list,total_count,len(pre_auth_keys_list))

@bp.route('/addKey', methods=['GET','POST'])
@login_required
def addKey():

    user_name = current_user.id
    expire_date = datetime.now() + timedelta(days=7)

    url =  f'/api/v1/preauthkey'
    data = {'user':user_name,'reusable':True,'ephemeral':False,'expiration':expire_date.isoformat() + 'Z'}

    response = to_request('POST',url,data)

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

