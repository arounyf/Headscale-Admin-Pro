import json
from flask_login import current_user, login_required
from sqlalchemy import func
import requests

from login_setup import role_required
from models import UserModel,NodeModel
from flask import Blueprint, request, session, make_response, g, redirect, url_for, jsonify, \
    current_app

bp = Blueprint("node", __name__, url_prefix='/api/node')



@bp.route('/getNodes')
@login_required
def getNodes():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    #
    # 分页查询
    # 分页查询

    # 使用 func.strftime 格式化时间字段
    query = NodeModel.query.with_entities(
        NodeModel.id,
        UserModel.name,
        NodeModel.given_name,
        NodeModel.user_id,
        NodeModel.ipv4,
        NodeModel.host_info,
        func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.last_seen,'localtime').label('last_seen'),
        # NodeModel.last_seen,

        func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.expiry,'localtime').label('expiry'),
        func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.created_at,'localtime').label('created_at'),
        func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.updated_at,'localtime').label('updated_at'),
        func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.deleted_at,'localtime').label('deleted_at')
        # 可以添加其他需要的字段
    ).join(UserModel, NodeModel.user_id == UserModel.id)  # 通过 user_id 进行表连接

    # 判断用户角色
    if current_user.role != 'manager':
        # 如果不是 manager，只查询当前用户的节点信息
        query = query.filter(NodeModel.user_id == current_user.id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    nodes = pagination.items
    print(nodes)
    #
    # 数据格式化
    nodes_list = [{
        'id': node.id,
        'userName': node.name,
        'name': node.given_name,
        'ip': node.ipv4,
        'lastTime': node.last_seen,
        'createTime':node.created_at,
        'OS': json.loads(node.host_info).get("OS")+json.loads(node.host_info).get("OSVersion"),
        'Client':json.loads(node.host_info).get("IPNVersion")


    } for node in nodes]

    # 接口返回json数据
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
        'count':pagination.total,
        'totalRow':{
                'count':len(nodes)
            }
    }
    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = nodes_list


    return res_json



@bp.route('/register', methods=['GET','POST'])
@login_required
def register():

    nodekey = request.form.get('nodekey')
    user_name = current_user.name



    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = f'{server_host}/api/v1/node/register?user={user_name}&key={nodekey}'  # 替换为实际的目标 URL
    response = requests.post(url, headers=headers)

    # 额外字段
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
    }
    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = str(response.text)

    return res_json


@bp.route('/delete', methods=['GET','POST'])
@login_required
def delete():

    node_id = request.form.get('NodeId')

    print(node_id)



    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = f'{server_host}/api/v1/node/{node_id}'  # 替换为实际的目标 URL

    response = requests.delete(url, headers=headers)
    # 额外字段
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
    }
    res_json['code'], res_json['msg'] = '0', '删除成功'
    res_json['data'] = str(response.text)

    return res_json


@bp.route('/new_owner', methods=['GET','POST'])
@login_required
@role_required("admin")
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
