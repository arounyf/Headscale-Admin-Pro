from datetime import datetime, timedelta
from utils import record_log, reload_headscale
from flask_login import login_user, logout_user, current_user, login_required
from exts import db
import requests
from models import UserModel, ACLModel,NodeModel
from flask import Blueprint, render_template,request, session, make_response, g, redirect, url_for, jsonify, \
    current_app
from .forms import RegisterForm, LoginForm, PasswdForm
from sqlalchemy import  text
bp = Blueprint("api", __name__, url_prefix='/api')


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
    node = NodeModel.query.filter_by(id=machine_id).first()
    if not node:
        res_json = {
            'code': '1',
            'msg': '机器不存在',
            'data': ''
        }
        return jsonify(res_json)
    url = f'{server_host}/api/v1/machine/{machine_id}/rename/{machine_name}'  # 替换为实际的目标 URL
    try:
        response = requests.post(url, headers=headers)
        # 额外字段
        res_json = {
            'code': '',
            'data': '',
            'msg': '',
        }
        res_json['code'], res_json['msg'] = '0', '更新成功'
        res_json['data'] = str(response.text)
        return jsonify(res_json)
    except Exception as e:
        res_json = {
            'code': '1',
            'msg': '后台服务异常，请稍后再试！',
            'data': ''
        }
        return jsonify(res_json)


