from flask_login import login_required, current_user
from flask import Blueprint,  request
from exts import SqliteDB
from utils import res, table_res, to_request

bp = Blueprint("route", __name__, url_prefix='/api/route')




@bp.route('/getRoute')
@login_required
def getRoute():
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        # 构建基础查询语句
        base_query = """
            SELECT 
                routes.id,
                users.name,
                nodes.given_name,
                routes.prefix,
                routes.enabled,
                strftime('%Y-%m-%d %H:%M:%S', routes.created_at, 'localtime') as created_at
            FROM 
                routes
            JOIN 
                nodes ON routes.node_id = nodes.id
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
        routes = cursor.fetchall()

    # 数据格式化
    routes_list = []
    for route in routes:
        routes_list.append({
            'id': route['id'],
            'name': route['name'],
            'NodeName': route['given_name'],
            'route': route['prefix'],
            'createTime': route['created_at'],
            'enable': int(route['enabled'])
        })



    return table_res('0','获取成功',routes_list,total_count,len(routes_list))

@bp.route('/route_enable', methods=['GET','POST'])
@login_required
def route_enable():
    route_id = request.form.get('routeId')
    enabled = request.form.get('Enable')

    if enabled == "true":
        url_path = f'/api/v1/routes/{route_id}/enable'
    else:
        url_path = f'/api/v1/routes/{route_id}/disable'

    with SqliteDB() as cursor:
        # 连接两表查询，获取 user_id
        query = """
            SELECT nodes.user_id
            FROM routes
            JOIN nodes ON routes.node_id = nodes.id
            WHERE routes.id =?
        """
        user_id = cursor.execute(query, (route_id,)).fetchone()[0]


    if current_user.route != '1':
        return res('1', '未获得使用权限')

    if current_user.role == 'manager' or user_id == current_user.id:
        response = to_request('POST',url_path)
        if response['code'] == '0':
            return res('0', '切换成功', response['data'])
        else:
            return res(response['code'], response['msg'])
    else:
        return res('1', '非法请求')


