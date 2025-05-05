import json
import requests
from flask_login import current_user, login_required
from blueprints.auth import register_node
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request,current_app
from utils import res, table_res


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
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = f'{server_host}/api/v1/node/{node_id}'

    if current_user.role != 'manager':
        with SqliteDB() as cursor:
            query = "SELECT COUNT(*) as count FROM nodes WHERE id =? AND user_id =?;"
            cursor.execute(query, (node_id, current_user.id))
            result = cursor.fetchone()
            count = result['count'] if result else 0

        if count > 0:
            response = requests.delete(url, headers=headers)
        else:
            return res('1', '非法请求')
    else:
        requests.delete(url, headers=headers)

    return res('0', '删除成功')


@bp.route('/new_owner', methods=['GET','POST'])
@login_required
@role_required("manager")
def new_owner():

    node_id = request.form.get('nodeId')
    user_name = request.form.get('userName')

    print(node_id)
    print(user_name)

    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }

    url = f'{server_host}/api/v1/node/{node_id}/user'  # 替换为实际的目标 URL


    data = {"user": user_name}
    response = requests.post(url, headers=headers,json=data)
    # 额外字段
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
    }
    res_json['code'], res_json['msg'] = '0', '更新成功'
    res_json['data'] = str(response.text)

    return res_json


@bp.route('/rename', methods=['POST'])
@login_required
def rename():

    node_id = request.form.get('nodeId')
    node_name = request.form.get('nodeName')

    print(node_id)
    print(node_name)

    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }

    url = f'{server_host}/api/v1/node/{node_id}/rename/{node_name}'  # 替换为实际的目标 URL



    response = requests.post(url, headers=headers)
    # 额外字段
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
    }
    res_json['code'], res_json['msg'] = '0', '更新成功'
    res_json['data'] = str(response.text)

    return res_json
