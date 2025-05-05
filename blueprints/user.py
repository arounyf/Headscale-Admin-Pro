from flask_login import current_user, login_required
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
from utils import res


bp = Blueprint("user", __name__, url_prefix='/api/user')


@bp.route('/getUsers')
@login_required
@role_required("manager")
def getUsers():
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条

    offset = (page - 1) * per_page

    users_list = []

    with SqliteDB() as cursor:
        # 查询总记录数
        cursor.execute("SELECT COUNT(*) FROM users")
        total_count = cursor.fetchone()[0]

        # 查询用户数据
        query = """
            SELECT id, name, created_at, cellphone, expire, role, node, route, enable
            FROM users
            LIMIT? OFFSET?
        """
        cursor.execute(query, (per_page, offset))
        rows = cursor.fetchall()

        for row in rows:

            try:
                created_at = str(row['created_at'])[:19]
                expire = str(row['expire'])[:19]
            except Exception as e:
                print(f"处理时间出错: {e}")
                created_at = ""
                expire = ""

            user_dict = {
                'id': row['id'],
                'userName': row['name'],
                'createTime': created_at,
                'cellphone': row['cellphone'],
                'expire': expire,
                'role': row['role'],
                'node': row['node'],
                'route': row['route'],
                'enable': row['enable'],
            }
            users_list.append(user_dict)

    res_json = {
        'code': '',
        'data': '',
        'msg': '',
        'count': total_count,
        'totalRow': {
            'count': len(users_list)
        }
    }
    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = users_list

    return res_json



@bp.route('/re_expire',methods=['GET','POST'])
@login_required
@role_required("manager")
def re_expire():

    user_id = request.form.get('user_id')
    new_expire = request.form.get('new_expire')

    with SqliteDB() as cursor:
        # 查询用户
        query = "SELECT * FROM users WHERE id =?;"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        if not user:
            return res('1', '未找到该用户','')
        # 更新用户的过期时间
        update_query = "UPDATE users SET expire =? WHERE id =?;"
        cursor.execute(update_query, (new_expire, user_id))

    return res('0', '更新成功','')


@bp.route('/re_node',methods=['GET','POST'])
@login_required
@role_required("manager")
def re_node():
    user_id = request.form.get('user_id')
    new_node = request.form.get('new_node')

    with SqliteDB() as cursor:
        # 更新用户的节点信息
        update_query = "UPDATE users SET node =? WHERE id =?;"
        cursor.execute(update_query, (new_node, user_id))

    return res('0', '更新成功')


@bp.route('/user_enable',methods=['GET','POST'])
@login_required
@role_required("manager")
def user_enable():
    user_id = request.form.get('user_id')
    enable = request.form.get('enable')

    with SqliteDB() as cursor:
        # 查询用户
        query = "SELECT * FROM users WHERE id =?;"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        if enable == "true":
            update_query = "UPDATE users SET enable = 1 WHERE id =?;"
            msg = '启用成功'
        else:
            if user['name'] == 'admin':
                return res('1', '停用失败，无法停用admin用户')
            update_query = "UPDATE users SET enable = 0 WHERE id =?;"
            msg = '停用成功'

        cursor.execute(update_query, (user_id,))

    return res('0', msg)


@bp.route('/route_enable',methods=['GET','POST'])
@login_required
@role_required("manager")
def route_enable():
    user_id = request.form.get('user_id')
    enable = request.form.get('enable')

    with SqliteDB() as cursor:
        if enable == "true":
            update_query = "UPDATE users SET route = 1 WHERE id =?;"
            msg = '启用成功'
        else:
            update_query = "UPDATE users SET route = 0 WHERE id =?;"
            msg = '停用成功'
        cursor.execute(update_query, (user_id,))

    return res('0', msg)


@bp.route('/delUser',methods=['GET','POST'])
@login_required
@role_required("manager")
def delUser():
    user_id = request.form.get('user_id')

    with SqliteDB() as cursor:
        # 删除用户
        delete_query = "DELETE FROM users WHERE id =?;"
        cursor.execute(delete_query, (user_id,))

    return res('0', '删除成功')


@bp.route('/init_data',methods=['GET'])
@login_required
def init_data():
    with SqliteDB() as cursor:
        # 查询当前用户的创建时间和过期时间
        current_user_id = current_user.id  # 假设 current_user 有 id 属性
        user_query = "SELECT created_at, expire FROM users WHERE id =?;"
        cursor.execute(user_query, (current_user_id,))
        user_info = cursor.fetchone()

        try:
            created_at = str(user_info['created_at'])[:19]
            expire = str(user_info['expire'])[:19]
        except Exception as e:
            print(f"处理时间出错: {e}")
            created_at = ""
            expire = ""

        # 查询节点数量
        node_count_query = "SELECT COUNT(*) as count FROM nodes;"
        cursor.execute(node_count_query)
        node_count_result = cursor.fetchone()
        node_count = node_count_result['count'] if node_count_result else 0

        # 查询路由数量
        route_count_query = "SELECT COUNT(*) as count FROM routes;"
        cursor.execute(route_count_query)
        route_count_result = cursor.fetchone()
        route_count = route_count_result['count'] if route_count_result else 0

    data = {
        "created_at": created_at,
        "expire": expire,
        "node_count": node_count,
        "route_count": route_count
    }

    return res('0', '查询成功', data)

