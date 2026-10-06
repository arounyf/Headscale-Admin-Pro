import re
import datetime
import json
import requests
from flask_login import current_user, login_required
from blueprints.auth import register_node
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
from utils import res, table_res, to_request, is_user_mode, api_ts

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
                # 这两列走 API，不是走库，所以用 api_ts 而不是 display_ts。
                # 以前是裸透传 API 的原始 ISO 串（'2026-10-06T06:10:08.123Z'）——
                # 列表页目前没有时间列所以没露出来，但那是**另一套格式**，谁给列表
                # 加个时间列就会看到 UTC 原始串，跟详情页的北京墙钟对不上。
                'lastTime': api_ts(node['lastSeen']),
                'createTime': api_ts(node['createdAt']),
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
    """通过节点 ID 取详情，数据全部来自 headscale 的 API。

    以前这一页 SELECT 面板库里的 nodes 表，拿的是 headscale **周期性落盘的快照**：
    同一个 lastSeen，走库比走 API 旧 23 分钟（实测）。一个事实两个来源、两个值，
    而且库那个是旧的。

    顺带修掉的是格式：那一版用 display_ts 格式化 headscale 的列。display_ts 里
    那个「裸值就当北京墙钟」的兜底分支是给**面板自有列**做历史迁移用的，用在
    headscale 的列上只会掩盖问题（它永远写带偏移的值，出现裸值就是代码坏了）。
    现在时间走 api_ts，与列表页同一个函数。
    """
    # 1. 获取请求中的 NodeId
    node_id = request.args.get('NodeId') or request.form.get('NodeId')
    
    if not node_id:
        return res("1", "缺少参数: NodeId", [])

    try:
        node_id = int(node_id)
    except ValueError:
        return res("1", "NodeId 必须是整数", [])

    # 2. 取节点
    response = to_request('GET', f'/api/v1/node/{node_id}')
    if response['code'] != '0':
        return res("1", f"未找到ID为 {node_id} 的节点", [])

    node = json.loads(response['data']).get('node') or {}
    if not node:
        return res("1", f"未找到ID为 {node_id} 的节点", [])

    user_info = node.get('user') or {}

    # 3. 权限：非管理员（或用户模式）只能看自己的节点。
    # 以前这条判断是加在 SQL 的 WHERE 里的，改走 API 之后得自己判。
    # 注意本函数没有 @role_required，普通用户也要能看自己的节点。
    if current_user.role != 'manager' or is_user_mode():
        if str(user_info.get('id', '')) != str(current_user.id):
            return res("1", f"未找到ID为 {node_id} 的节点", [])

    host = node.get('hostInfo') or {}

    # headscale 把两个地址混在一个列表里，按冒号分（IPv6 一定含冒号，IPv4 一定不含）
    addresses = node.get('ipAddresses') or []
    ipv4 = next((a for a in addresses if ':' not in a), '')
    ipv6 = next((a for a in addresses if ':' in a), '')

    formatted_item = {
        "name": node.get('givenName') or node.get('name') or '',
        "hostname": node.get('name') or '',
        "userName": user_info.get('name', '-'),
        "userEmail": user_info.get('email') or '',
        "ipv4": ipv4,
        "ipv6": ipv6,
        # 时间走 api_ts，与列表页(getNodes)同一个函数、同一套格式。
        "lastSeen": api_ts(node.get('lastSeen')),
        "createdAt": api_ts(node.get('createdAt')),
        "OS": host.get('os', ''),
        "OSVersion": host.get('osVersion', ''),
        "Client": host.get('ipnVersion') or '',
        "Machine": host.get('machine', ''),
        "DeviceModel": host.get('deviceModel', ''),
        "Distro": host.get('distro', ''),
        "DistroVersion": host.get('distroVersion', ''),
        "GoVersion": host.get('goVersion', ''),
        "Desktop": host.get('desktop', False),
        "Container": host.get('container', False),
        "Userspace": host.get('userspace', False),
        "Routes": ', '.join(node.get('approvedRoutes') or []),
    }

    return res("0", "获取成功", [formatted_item])





@bp.route('/node_route_info', methods=['GET', 'POST'])
@login_required
def node_route_info():
    node_id = request.form.get('NodeId')

    with SqliteDB() as cursor:
        node = cursor.execute("SELECT user_id FROM nodes WHERE id =?", (node_id,)).fetchone()
    if not node or (node[0] != current_user.id and current_user.role != 'manager'):
        return res("1", "非法请求", [])

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
        node = cursor.execute("SELECT user_id FROM nodes WHERE id =?", (node_id,)).fetchone()
        route = cursor.execute("SELECT route FROM users WHERE id =?", (current_user.id,)).fetchone()

    # 只能审批自己的节点。delete / rename 判的是同一件事，之前这里漏了，
    # 只查了自己的 route 开关，于是开了 route 的普通用户能审批别人的路由。
    if not node or (node[0] != current_user.id and current_user.role != 'manager'):
        return res('1', '非法请求')

    # route 开关对所有人一视同仁 —— 它管的是「谁能审批路由」，不是「谁是管理员」，
    # 所以管理员这里也不放行，只是把提示说清楚该去哪儿开。
    if not route or route[0] == "0":
        if current_user.role == 'manager':
            return res('1', '你当前无此权限，请在「用户管理」里为自己打开「路由」开关')
        return res('1', '你当前无此权限！请联系管理员')

    response = to_request('POST',url,data)

    if response['code'] == '0':
        return res('0', '提交成功', response['data'])
    else:
        return res(response['code'], response['msg'])



