from flask_login import login_required, current_user
from sqlalchemy import func
import requests

from exts import db
from models import UserModel,NodeModel,RouteModel
from flask import Blueprint,  request, current_app

from utils import res, to_post

bp = Blueprint("route", __name__, url_prefix='/api/route')




@bp.route('/getRoute')
@login_required
def getRoute():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    #
    # 分页查询
    # 分页查询

    # 使用 func.strftime 格式化时间字段
    query = RouteModel.query.with_entities(
        RouteModel.id,
        UserModel.name,
        NodeModel.given_name,
        RouteModel.prefix,
        RouteModel.enabled,
        func.strftime('%Y-%m-%d %H:%M:%S', RouteModel.created_at,'localtime').label('created_at')
        # 可以添加其他需要的字段
    ).join(
        NodeModel, RouteModel.node_id == NodeModel.id  # 假设 RouteModel 通过 node_id 关联 NodeModel
    ).join(
        UserModel, NodeModel.user_id == UserModel.id
    )

    # 判断用户角色
    if current_user.role != 'manager':
        # 如果不是 manager，只查询当前用户的节点信息
        query = query.filter(NodeModel.user_id == current_user.id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    routes = pagination.items
    #
    # 数据格式化
    routes_list = [{
        'id': route.id,
        'name': route.name,
        'NodeName': route.given_name,
        'route': route.prefix,
        'createTime':route.created_at,
        'enable':int(route.enabled)
    } for route in routes]


    # 额外字段
    res = {
        'code': '0',
        'data': routes_list,
        'msg': '获取成功',
        'count':pagination.total,
        'totalRow':{
                'count':len(routes)
            }
    }

    return res

@bp.route('/route_enable', methods=['GET','POST'])
@login_required
def route_enable():
    route_id = request.form.get('routeId')
    enabled = request.form.get('Enable')
    response = None

    if (enabled == "true"):
        url_path = f'/api/v1/routes/{route_id}/enable'  # 替换为实际的目标 URL
        code, msg, data = '0', '打开成功', response

    else:
        url_path = f'/api/v1/routes/{route_id}/disable'  # 替换为实际的目标 URL
        code, msg, data = '0', '关闭成功' ,response


    # 连接两表查询，因为路由表没有user_id
    user_id = db.session.query(NodeModel.user_id).select_from(RouteModel).join(
        NodeModel, RouteModel.node_id == NodeModel.id).filter(
        RouteModel.id == route_id).first(
    )

    if current_user.route != '1':
        code, msg, data = '1', '未获得使用权限', response
    elif current_user.role == 'manager' or user_id == current_user.user_id:  # 如果是管理员或者是本用户的路由
        response = to_post(url_path).text
        if (response == "Unauthorized"):
            code, msg, data = '1', '认证失败', response
    else:
        code, msg, data = '1', '非法请求', response

    return res(code, msg, data)

