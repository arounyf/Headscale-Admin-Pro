from flask_login import login_required, current_user
from sqlalchemy import func
import requests

from exts import db
from models import UserModel,NodeModel,RouteModel
from flask import Blueprint,  request, current_app


bp = Blueprint("route", __name__, url_prefix='/api/route')


res_json = {'code': '', 'data': '', 'msg': ''}

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
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
        'count':pagination.total,
        'totalRow':{
                'count':len(routes)
            }
    }
    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = routes_list


    return res_json

@bp.route('/route_enable', methods=['GET','POST'])
@login_required
def route_enable():
    route_id = request.form.get('routeId')
    enabled = request.form.get('Enable')

    print(route_id)
    print(enabled)

    res_json['code'] = '0'

    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }

    if (enabled == "true"):
        res_json['msg'] = '打开成功'
        url = f'{server_host}/api/v1/routes/{route_id}/enable'  # 替换为实际的目标 URL
    else:
        res_json['msg'] = '关闭成功'
        url = f'{server_host}/api/v1/routes/{route_id}/disable'  # 替换为实际的目标 URL

    res_json['code'], res_json['msg'], res_json['data'] = '0', '删除成功', ""
    if current_user.role != 'admin':  # 如果不是管理员
        # 通过 RouteModel 的 node_id 关联到 NodeModel，再判断 user_id 是否为当前用户
        count = db.session.query(RouteModel).join(NodeModel).filter(
            RouteModel.id == route_id,
            NodeModel.user_id == current_user.id
        ).count()

        if count > 0:
            response = requests.delete(url, headers=headers)
            if (response.text == "Unauthorized"):
                res_json['code'], res_json['msg'] = '1', '认证失败'
        else:
            res_json['code'], res_json['msg'] = '1', '非法请求'
    else:
        requests.delete(url, headers=headers)
    return res_json

