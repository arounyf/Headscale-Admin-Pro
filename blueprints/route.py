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

        # 判断用户角色
        if current_user.role != 'manager':
            base_query += " AND user_id =? "
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
        # 处理可能是bytes或str的字段
        approved_routes = route['approved_routes']
        # 如果是bytes类型则解码为str，否则直接使用
        route_str = approved_routes.decode('utf-8') if isinstance(approved_routes, bytes) else approved_routes
        
        routes_list.append({
            'id': route['id'],
            'name': route['name'],
            'NodeName': route['given_name'],
            'route': route_str,  # 使用处理后的结果
            'createTime': route['created_at'],
            'enable': 1
        })


    return table_res('0','获取成功',routes_list,total_count,len(routes_list))


