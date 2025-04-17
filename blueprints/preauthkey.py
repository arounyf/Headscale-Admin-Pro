from datetime import datetime, timedelta
from flask_login import current_user, login_required
from sqlalchemy import func
import requests

from exts import db
from models import UserModel, NodeModel, RouteModel, ACLModel, PreAuthKeysModel
from flask import Blueprint, render_template, request, session, make_response, g, redirect, url_for, jsonify, \
    current_app

from .forms import RegisterForm, LoginForm
from blueprints.forms import RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
from .get_captcha import get_captcha_code_and_content
bp = Blueprint("preauthkey", __name__, url_prefix='/api/preauthkey')


res_json = {'code': '', 'data': '', 'msg': ''}

@bp.route('/getPreAuthKey')
@login_required
def getPreAuthKey():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    #
    # 分页查询
    # 分页查询

    # 使用 func.strftime 格式化时间字段
    query = PreAuthKeysModel.query.with_entities(
        PreAuthKeysModel.id,
        PreAuthKeysModel.key,
        UserModel.name,
        func.strftime('%Y-%m-%d %H:%M:%S', PreAuthKeysModel.created_at,'localtime').label('created_at'),
        func.strftime('%Y-%m-%d %H:%M:%S', PreAuthKeysModel.expiration,'localtime').label('expiration'),

        # 可以添加其他需要的字段
    ) .join(UserModel, PreAuthKeysModel.user_id == UserModel.id)

    # 判断用户角色
    if current_user.role != 'manager':
        # 如果不是 manager，只查询当前用户的节点信息
        query = query.filter(PreAuthKeysModel.user_id == current_user.id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    PreAuthKeys = pagination.items
    #
    # 数据格式化
    PreAuthKeys_list = [{
        'id': PreAuthKey.id,
        'key': PreAuthKey.key,
        'name': PreAuthKey.name,
        'create_time': PreAuthKey.created_at,
        'expiration': PreAuthKey.expiration,

    } for PreAuthKey in PreAuthKeys]

    # 接口返回json数据
    res_json = {
        'code': '0',
        'data': PreAuthKeys_list,
        'msg': '获取成功',
        'count': pagination.total,
        'totalRow': {
            'count': len(PreAuthKeys)
        }
    }

    return res_json

@bp.route('/addKey', methods=['GET','POST'])
@login_required
def addKey():
    res_json['code'], res_json['msg'] = '0', '获取成功'
    # user_id = current_user.id
    user_name = current_user.name

    expire_date = datetime.now() + timedelta(days=7)


    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }

    url =  f'{server_host}/api/v1/preauthkey'

    bearer_token = current_app.config['BEARER_TOKEN']
    # 设置请求头，包含 Bearer Token
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    print(url)
    data = {'user':user_name,'reusable':True,'ephemeral':False,'expiration':expire_date.isoformat() + 'Z'}

    response = requests.post(url, headers=headers, json=data)

    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = response.text

    return res_json





@bp.route('/delKey', methods=['GET','POST'])
@login_required
def delKey():
    key_id = request.form.get('keyId')

    # 直接使用 delete 方法结合条件删除记录
    db.session.query(PreAuthKeysModel).filter(PreAuthKeysModel.id == key_id).delete()
    db.session.commit()

    res_json['code'], res_json['msg'] = '0', '删除成功'
    return res_json


