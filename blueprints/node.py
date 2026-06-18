import re
import datetime
import json
import requests
from flask_login import current_user, login_required
from blueprints.auth import register_node
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
from utils import res, table_res, to_request, is_user_mode

bp = Blueprint("node", __name__, url_prefix='/api/node')


@bp.route('/register', methods=['POST'])
@login_required
def register():
    """通过 nodekey 调用 headscale API 注册节点"""
    from blueprints.auth import register_node
    nodekey = request.form.get('nodekey', '')
    if not nodekey:
        return res('1', '缺少 nodekey', '')
    return register_node(nodekey)




@bp.route('/getNodes')
@login_required
def getNodes():
    search_name= request.args.get('search_name',default='')
    print(search_name)

    if current_user.name == 'admin' and not is_user_mode():
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
        
        # 批量查 host_info
        host_map = {}
        if nodes:
            nids = [int(n['id']) for n in nodes]
            ph = ','.join(['?']*len(nids))
            with SqliteDB() as cur:
                cur.execute(f"SELECT id,host_info FROM nodes WHERE id IN({ph}) AND host_info!=''", nids)
                for row in cur.fetchall():
                    host_map[row['id']] = json.loads(row['host_info'])

        nodes_list = []
        for node in nodes:
            hid = host_map.get(int(node['id']), {})
            routes = node.get('approvedRoutes', [])
            isExit = any(r in ('0.0.0.0/0','::/0') for r in routes)
            hasSub = any(r not in ('0.0.0.0/0','::/0') for r in routes)
            nodes_list.append({
                'id': node['id'],
                'userName': (node.get('user') or {}).get('name', '-'),
                'name': node['givenName'],
                'ip': ', '.join(node['ipAddresses']),
                'lastTime': node['lastSeen'],
                'createTime': node['createdAt'],
                'OS': hid.get('OS',''),
                'Client': hid.get('IPNVersion',''),
                'online': node['online'],
                'isExitNode': isExit,
                'hasSubnets': hasSub,
                'approvedRoutes': ', '.join(routes),
            })
        
        return table_res('0', '获取成功', nodes_list, total_count, len(nodes_list))
    else:
        return res(response['code'], response['msg'])




@bp.route('/topNodes')
@login_required
@role_required("manager")
def topNodes():
    if is_user_mode():
        url = f'/api/v1/node?user={current_user.name}'
    else:
        url = f'/api/v1/node'
    response = to_request('GET', url)

    if response['code'] == '0':
        # 解析返回的节点数据
        data = json.loads(response['data'])
        nodes = data.get('nodes', [])
        
        # 使用字典来按用户名分组统计
        # 字典的键是用户名，值是一个包含统计信息的字典
        user_stats = {}
        
        for node in nodes:
            # 安全地获取用户名，如果用户信息不存在则使用'未知用户'
            user_name = node.get('user', {}).get('name', '未知用户')
            
            # 如果该用户是第一次出现，则初始化其统计信息
            if user_name not in user_stats:
                user_stats[user_name] = {
                    'name': user_name,
                    'online': 0,
                    'nodes': 0,
                    'routes': 0
                }
            
            # 更新该用户的统计数据
            user_stats[user_name]['nodes'] += 1  # 累计节点数加1
            
            # 如果节点在线，在线节点数加1
            if node.get('online', False):
                user_stats[user_name]['online'] += 1
                
            # 累加该节点的路由数量
            # 路由列表可能不存在，所以要做安全检查
            approved_routes = node.get('approvedRoutes', [])
            user_stats[user_name]['routes'] += len(approved_routes)

        # 将字典的值（统计信息）转换为列表，以便前端表格展示
        # 并按累计节点数降序排序
        result_list = sorted(user_stats.values(), key=lambda x: x['online'], reverse=True)
        
        # 计算总节点数，用于表格分页等功能
        total_nodes_count = len(nodes)
        
        # 返回数据给前端
        return table_res('0', '获取成功', result_list, total_nodes_count, len(result_list))
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








@bp.route('/rename', methods=['POST'])
@login_required
def rename():

    node_id = request.form.get('nodeId')
    node_name = request.form.get('nodeName')

    if not node_name or not re.fullmatch(r'[a-zA-Z0-9._-]+', node_name):
        return res('1', '节点名称仅允许字母、数字、点、下划线和连字符')

    url = f'/api/v1/node/{node_id}/rename/{node_name}'

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

    # 2. 构建查询SQL
    base_query = """
        SELECT
            nodes.id, nodes.hostname, nodes.given_name,
            nodes.ipv4, nodes.ipv6, nodes.last_seen, nodes.created_at,
            nodes.host_info, nodes.approved_routes,
            users.name as user_name, users.email as user_email
        FROM nodes
        JOIN users ON nodes.user_id = users.id
    """

    conditions = []
    params = []

    if current_user.role != 'manager' or is_user_mode():
        conditions.append("nodes.user_id = ?")
        params.append(current_user.id)

    conditions.append("nodes.id = ?")
    params.append(node_id)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    with SqliteDB() as cursor:
        cursor.execute(base_query, params)
        node = cursor.fetchone()

    if not node:
        return res("1", f"未找到ID为 {node_id} 的节点", [])

    host_info = json.loads(node['host_info']) if node['host_info'] else {}
    try:
        routes = json.loads(node['approved_routes']) if node['approved_routes'] else []
    except (json.JSONDecodeError, TypeError):
        routes = []

    formatted_item = {
        "name": node['given_name'] or node['hostname'],
        "hostname": node['hostname'],
        "userName": node['user_name'],
        "userEmail": node['user_email'] or '',
        "ipv4": node['ipv4'] or '',
        "ipv6": node['ipv6'] or '',
        "lastSeen": str(node['last_seen']) if node['last_seen'] else '',
        "createdAt": str(node['created_at']) if node['created_at'] else '',
        "OS": host_info.get('OS', ''),
        "OSVersion": host_info.get('OSVersion', ''),
        "Client": host_info.get('IPNVersion') or '',
        "Machine": host_info.get('Machine', ''),
        "DeviceModel": host_info.get('DeviceModel', ''),
        "Distro": host_info.get('Distro', ''),
        "DistroVersion": host_info.get('DistroVersion', ''),
        "GoVersion": host_info.get('GoVersion', ''),
        "Desktop": host_info.get('Desktop', False),
        "Container": host_info.get('Container', False),
        "Userspace": host_info.get('Userspace', False),
        "Routes": ', '.join(routes),
    }

    return res("0", "获取成功", [formatted_item])





@bp.route('/node_route_info', methods=['GET', 'POST'])
@login_required
def node_route_info():
    node_id = request.form.get('NodeId')
    url = f'/api/v1/node/{node_id}'

    response = to_request('GET', url)

    if response['code'] == '0':
        try:
            # 解析原始响应数据
            raw_data = json.loads(response['data'])
            node_data = raw_data['node']  # 提取node对象
        except (json.JSONDecodeError, KeyError) as e:
            return res("1", f"数据解析错误: {str(e)}", [])

        # 时间格式化：仅替换T为空格，去除Z
        def format_time(utc_time_str):
            if not utc_time_str:
                return ""
            return utc_time_str.replace('T', ' ').replace('Z', '')

        # 提取并保留一级路由字段（approvedRoutes和availableRoutes）
        formatted_item = { 
            # 关键路由字段（一级主要字段，突出显示）
            "approvedRoutes": node_data.get('approvedRoutes', []),  # 已批准路由
            "availableRoutes": node_data.get('availableRoutes', []),  # 可用路由 
     
        }

        data_list = [formatted_item]
        return res("0", "获取成功", data_list)

    else:
        return res("1", "请求失败", [])

@bp.route('/approve_routes', methods=['GET','POST'])
@login_required
def approve_routes():

    node_id = request.form.get('nodeId')
    routes = request.form.get('routes')

    url =  f'/api/v1/node/' + str(node_id)+'/approve_routes'
    data = {"routes": [routes]}


    with SqliteDB() as cursor:
        route = cursor.execute("SELECT route FROM users WHERE id =? ",(current_user.id,)).fetchone()[0]
    

    if route == "0":
        return res('1', '你当前无此权限！请联系管理员')
    else:
        response = to_request('POST',url,data)

        if response['code'] == '0':
            return res('0', '提交成功', response['data'])
        else:
            return res(response['code'], response['msg'])



