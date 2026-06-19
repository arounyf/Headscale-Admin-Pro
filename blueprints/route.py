import json
from flask_login import login_required, current_user
from flask import Blueprint, request
from exts import SqliteDB
from utils import res, table_res, to_request, is_user_mode

bp = Blueprint("route", __name__, url_prefix='/api/route')


@bp.route('/getAllRoutes')
@login_required
def getAllRoutes():
    """获取所有节点的通告路由及其审批状态"""
    # 获取所有节点
    resp = to_request('GET', '/api/v1/node')
    if resp['code'] != '0':
        return res(resp['code'], resp['msg'])

    all_nodes = json.loads(resp['data']).get('nodes', [])
    routes_list = []

    for node in all_nodes:
        node_id = node['id']
        user_info = node.get('user') or {}
        user_name = user_info.get('name', '-')
        node_name = node.get('givenName', node.get('name', '-'))
        approved = set(node.get('approvedRoutes', []))
        advertised = set(node.get('availableRoutes', []))

        # tag 过滤：普通用户只看自己的节点
        if current_user.role != 'manager' or is_user_mode():
            if str(user_info.get('id', '')) != str(current_user.id):
                continue

        # 搜索过滤
        search_name = request.args.get('search_name', '').strip()
        if search_name and search_name.lower() not in user_name.lower():
            continue

        for route in advertised:
            routes_list.append({
                'id': len(routes_list) + 1,
                'nodeId': node_id,
                'userName': user_name,
                'nodeName': node_name,
                'route': route,
                'enabled': route in approved,
            })

    total = len(routes_list)
    return table_res('0', '获取成功', routes_list, total, total)


@bp.route('/toggleRoute', methods=['POST'])
@login_required
def toggleRoute():
    """开关单条路由的审批状态"""
    node_id = request.form.get('nodeId')
    route_cidr = request.form.get('route')
    enable = request.form.get('enable', '1')  # '1' = enable, '0' = disable

    if not node_id or not route_cidr:
        return res('1', '缺少参数')

    # 获取节点当前审批的路由
    resp = to_request('GET', f'/api/v1/node/{node_id}')
    if resp['code'] != '0':
        return res(resp['code'], '获取节点信息失败')

    node_data = json.loads(resp['data'])
    current_approved = node_data.get('node', {}).get('approvedRoutes', [])

    # 计算新路由列表
    EXIT_ROUTES = {'0.0.0.0/0', '::/0'}
    if enable == '1':
        if route_cidr not in current_approved:
            new_routes = current_approved + [route_cidr]
        else:
            return res('0', '路由已启用', '')
    else:
        if route_cidr in EXIT_ROUTES:
            # headscale 强制出口路由成对存在，停用一个必须同时停用两个
            new_routes = [r for r in current_approved if r not in EXIT_ROUTES]
        else:
            new_routes = [r for r in current_approved if r != route_cidr]

    # 调用 headscale API 设置路由
    set_resp = to_request('POST', f'/api/v1/node/{node_id}/approve_routes',
                          data={'routes': new_routes})
    if set_resp['code'] != '0':
        return res(set_resp['code'], set_resp['msg'])

    status = '启用' if enable == '1' else '停用'
    return res('0', f'路由{status}成功', '')


@bp.route('/getRoute')
@login_required
def getRoute():
    """保留旧接口兼容"""
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        base_query = """
            SELECT
                nodes.id,
                users.name,
                nodes.given_name,
                nodes.approved_routes,
                strftime('%Y-%m-%d %H:%M:%S', nodes.created_at, 'localtime') as created_at
            FROM
                nodes
            JOIN
                users ON nodes.user_id = users.id
            WHERE nodes.approved_routes is NOT NULL

        """

        if current_user.role != 'manager' or is_user_mode():
            base_query += " AND user_id =? "
            params = (current_user.id,)
        else:
            params = ()

        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']

        paginated_query = f"{base_query} LIMIT? OFFSET? "
        paginated_params = params + (per_page, offset)
        cursor.execute(paginated_query, paginated_params)
        routes = cursor.fetchall()

    routes_list = []
    for route in routes:
        approved_routes = route['approved_routes']
        route_str = approved_routes.decode('utf-8') if isinstance(approved_routes, bytes) else approved_routes

        routes_list.append({
            'id': route['id'],
            'name': route['name'],
            'NodeName': route['given_name'],
            'route': route_str,
            'createTime': route['created_at'],
            'enable': 1
        })

    return table_res('0', '获取成功', routes_list, total_count, len(routes_list))
