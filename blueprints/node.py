import datetime
import json
import requests
from flask_login import current_user, login_required
from blueprints.auth import register_node
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
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
    search_name= request.args.get('search_name',default='')
    print(search_name)

    if current_user.name == 'admin':
        if search_name != "":
            user_name = search_name
        else:
            user_name = ""
    else:
        user_name = current_user.name

    


    url = f'/api/v1/node?user={user_name}'
    response = to_request('GET', url)

    if response['code'] == '0':
        # 解析返回的节点数据
        data = json.loads(response['data'])
        nodes = data.get('nodes', [])
        total_count = len(nodes)
        
        # 数据格式化
        nodes_list = []
        for node in nodes:
            nodes_list.append({
                'id': node['id'],
                'userName': node['user']['name'],  # 从user对象中获取用户名
                'name': node['givenName'],
                'ip': ', '.join(node['ipAddresses']),  # 拼接IPv4和IPv6地址
                'lastTime': node['lastSeen'],
                'createTime': node['createdAt'],
                'OS': '',  # 原数据中未包含host_info，暂时留空
                'Client': '',  # 原数据中未包含IPNVersion，暂时留空
                'online': node['online'],
                'approvedRoutes': ', '.join(node['approvedRoutes']),
                'availableRoutes': ', '.join(node['availableRoutes'])
            })
        
        return table_res('0', '获取成功', nodes_list, total_count, len(nodes_list))
    else:
        return res(response['code'], response['msg'])



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

@bp.route('/node_info', methods=['GET', 'POST'])
@login_required
def node_info():
    """
    通过节点ID从本地SQLite数据库获取节点详细信息
    (使用封装的 SqliteDB，并严格参考 getNodes 函数中的字段)
    """
    # 1. 获取请求中的 NodeId
    node_id = request.args.get('NodeId') or request.form.get('NodeId')
    
    if not node_id:
        return res("1", "缺少参数: NodeId", [])

    try:
        node_id = int(node_id)
    except ValueError:
        return res("1", "NodeId 必须是整数", [])

    # 2. 构建查询SQL语句和参数
    # 严格参考 getNodes 函数中的字段
    base_query = """
        SELECT 
            nodes.host_info
        FROM 
            nodes
        JOIN 
            users ON nodes.user_id = users.id
    """
    
    conditions = []
    params = []

    # 根据角色添加用户ID过滤
    if current_user.role != 'manager':
        conditions.append("nodes.user_id = ?")
        params.append(current_user.id)
    
    # 添加节点ID过滤
    conditions.append("nodes.id = ?")
    params.append(node_id)

    # 拼接 WHERE 子句
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # 3. 使用封装的 SqliteDB 执行查询
    with SqliteDB() as cursor:
        cursor.execute(base_query, params)
        node = cursor.fetchone()

    # 4. 检查查询结果
    if not node:
        return res("1", f"未找到ID为 {node_id} 的节点，或您没有权限查看。", [])

    # 5. 数据格式化
    # 这里的格式化逻辑也参考了 getNodes 函数
    host_info = json.loads(node['host_info']) if node['host_info'] else {}
    
    formatted_item = {
        "OS": (host_info.get("OS") or "") + (host_info.get("OSVersion") or ""),
        "Client": host_info.get("IPNVersion") or "",
        # 你可以根据需要，从 host_info 中提取更多字段
    }

    # 6. 返回格式化后的结果
    return res("0", "获取成功", [formatted_item])


@bp.route('/approve_routes', methods=['GET','POST'])
@login_required
def approve_routes():

    node_id = request.form.get('nodeId')
    routes = request.form.get('routes')

    url =  f'/api/v1/node/' + str(node_id)+'/approve_routes'
    data = {"routes": [routes]}

    response = to_request('POST',url,data)

    if response['code'] == '0':
        return res('0', '提交成功', response['data'])
    else:
        return res(response['code'], response['msg'])



