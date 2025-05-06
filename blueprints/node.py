import json
import requests
from flask_login import current_user, login_required
from blueprints.auth import register_node
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request,current_app
from utils import res, table_res, to_request

bp = Blueprint("node", __name__, url_prefix='/api/node')


@bp.route('/register', methods=['GET','POST'])
@login_required
def register():
    nodekey = request.form.get('nodekey')
    register_node_response = register_node(nodekey)

    print(register_node_response)
    if register_node_response['code'] == '0':
        try:
            # 获取 ipAddresses 的值
            ip_address = json.loads(register_node_response['data'])["node"]["ipAddresses"][0]
            code,msg,data = '0',ip_address,''
        except Exception as e:
            print(f"发生错误: {e}")
            headscale_error_msg = json.loads(register_node_response['data']).get('message')
            code, msg, data = '1', headscale_error_msg, ''
    else:
        error_msg = register_node_response['msg']
        code, msg, data = '1', error_msg, ''
    return res(code,msg,data)


@bp.route('/getNodes')
@login_required
def getNodes():
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        # 构建基础查询语句
        base_query = """
            SELECT 
                nodes.id,
                users.name,
                nodes.given_name,
                nodes.user_id,
                nodes.ipv4,
                nodes.host_info,
                strftime('%Y-%m-%d %H:%M:%S', nodes.last_seen, 'localtime') as last_seen,
                strftime('%Y-%m-%d %H:%M:%S', nodes.expiry, 'localtime') as expiry,
                strftime('%Y-%m-%d %H:%M:%S', nodes.created_at, 'localtime') as created_at,
                strftime('%Y-%m-%d %H:%M:%S', nodes.updated_at, 'localtime') as updated_at,
                strftime('%Y-%m-%d %H:%M:%S', nodes.deleted_at, 'localtime') as deleted_at
            FROM 
                nodes
            JOIN 
                users ON nodes.user_id = users.id
        """

        # 判断用户角色
        if current_user.role != 'manager':
            base_query += " WHERE nodes.user_id =? "
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
        nodes = cursor.fetchall()

    # 数据格式化
    nodes_list = []
    for node in nodes:
        host_info = json.loads(node['host_info'])
        nodes_list.append({
            'id': node['id'],
            'userName': node['name'],
            'name': node['given_name'],
            'ip': node['ipv4'],
            'lastTime': node['last_seen'],
            'createTime': node['created_at'],
            'OS': (host_info.get("OS") or "") + (host_info.get("OSVersion") or ""),
            'Client': host_info.get("IPNVersion") or ""
        })



    return table_res('0', '获取成功',nodes_list,total_count,len(nodes_list))





@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    node_id = request.form.get('NodeId')

    url = f'/api/v1/node/{node_id}'

    with SqliteDB() as cursor:
        user_id = cursor.execute("SELECT user_id FROM nodes WHERE id =? ", (node_id,)).fetchone()[0]
    if user_id == current_user.id or current_user.role == 'manager':
        response = to_request('DELETE', url)
        if response['code'] == '0':
            return res('0', '删除成功', response['data'])
        else:
            return res(response['code'], response['msg'])
    else:
        return res('1', '非法请求')




@bp.route('/new_owner', methods=['GET','POST'])
@login_required
@role_required("manager")
def new_owner():

    node_id = request.form.get('nodeId')
    user_name = request.form.get('userName')

    url = f'/api/v1/node/{node_id}/user'  # 替换为实际的目标 URL

    data = {"user": user_name}

    with SqliteDB() as cursor:
        user_id = cursor.execute("SELECT user_id FROM nodes WHERE id =? ", (node_id,)).fetchone()[0]
    if user_id == current_user.id or current_user.role == 'manager':
        response = to_request('POST', url, data)
        if response['code'] == '0':
            return res('0', '更新成功', response['data'])
        else:
            return res(response['code'], response['msg'])
    else:
        return res('1', '非法请求')




@bp.route('/rename', methods=['POST'])
@login_required
def rename():

    node_id = request.form.get('nodeId')
    node_name = request.form.get('nodeName')

    url = f'/api/v1/node/{node_id}/rename/{node_name}'  # 替换为实际的目标 URL

    with SqliteDB() as cursor:
        user_id = cursor.execute("SELECT user_id FROM nodes WHERE id =? ",(node_id,)).fetchone()[0]
    if user_id == current_user.id or current_user.role == 'manager':
        response = to_request('POST',url)
        if response['code'] == '0':
            return res('0', '更新成功', response['data'])
        else:
            return res(response['code'], response['msg'])
    else:
        return res('1', '非法请求')
