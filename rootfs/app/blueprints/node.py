import json
from flask_login import current_user, login_required
from sqlalchemy import func
import requests
from .database import DatabaseManager,ResponseResult
from exts import db

from login_setup import role_required
from models import UserModel,NodeModel
from flask import Blueprint, render_template,request, session, make_response, g, redirect, url_for, jsonify, \
    current_app

bp = Blueprint("node", __name__, url_prefix='/api/node')
bp_node = Blueprint("bp_node", __name__)


@bp.route('/getNodes')
@login_required
def getNodes():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    return DatabaseManager(db).getNodePagination(current_user,page,per_page).to_dict()

# 重命名节点
@bp.route('/rename', methods=['POST'])
@login_required
def rename():
    machine_id = request.form.get('machine_id')
    machine_name = request.form.get('machine_name')

    if not machine_id or not machine_name:
        return jsonify({'code': '1', 'msg': '参数不完整', 'data': ''})

    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    # 判断节点是否存在
    node = DatabaseManager(db).getNodeById(machine_id=machine_id)
    if not node:
        return ResponseResult(
            code="1",
            msg="机器不存在",
            count=0,  # 总记录数
            data='',
            totalRow={}  # 当前页的记录数
        ).to_dict()
    url = f'{server_host}/api/v1/node/{machine_id}/rename/{machine_name}'  # 替换为实际的目标 URL
    try:
        response = requests.post(url, headers=headers)
        return ResponseResult(
                code="0",
                msg="更新成功",
                count=0,  # 总记录数
                data=str(response.text),
                totalRow={}  # 当前页的记录数
            ).to_dict()
    except Exception as e:
        return ResponseResult(
                code="1",
                msg="后台服务异常，请稍后再试！",
                count=0,  # 总记录数
                data='',
                totalRow={}  # 当前页的记录数
            ).to_dict()

# 开放此路由如果添加节点则跳转登录后再跳转回来逻辑
@bp_node.route('/register/<nodekey>', methods=['GET'])
def register_node(nodekey=None):
    if not current_user.is_authenticated:
       next_page = request.path
       return redirect(url_for('auth.login', next=next_page))
    else:
        server_host = current_app.config['SERVER_HOST']
        bearer_token = current_app.config['BEARER_TOKEN']
        headers = {
        'Authorization': f'Bearer {bearer_token}'
        }
        user_name = current_user.name
        url = f'{server_host}/api/v1/node/register?user={user_name}&key={nodekey}'  # 替换为实际的目标 URL
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                message = "添加节点成功！" 
            else:
                message = "后台服务调用异常，请稍后再试！"
        except Exception as e:
          message = "后台服务异常，请稍后再试！"
        return redirect(url_for('admin.node', message=message))


@bp.route('/register',methods=['GET', 'POST'])
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
     return ResponseResult(
                code="0",
                msg="获取成功",
                count=0,  # 总记录数
                data=str(response.text),
                totalRow={}  # 当前页的记录数
            ).to_dict()
    


@bp.route('/delete', methods=['GET','POST'])
@login_required
def delete():

    node_id = request.form.get('NodeId')
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = f'{server_host}/api/v1/node/{node_id}'  # 替换为实际的目标 URL

    response = requests.delete(url, headers=headers)
    return ResponseResult(
                code="0",
                msg="删除成功",
                count=0,  # 总记录数
                data=str(response.text),
                totalRow={}  # 当前页的记录数
            ).to_dict()


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
    url = f'{server_host}/api/v1/node/{node_id}/user'
    data = {"user": user_name}
    response = requests.post(url, headers=headers,json=data)
    return ResponseResult(
                code="0",
                msg="更新成功",
                count=0,  # 总记录数
                data=str(response.text),
                totalRow={}  # 当前页的记录数
            ).to_dict()
