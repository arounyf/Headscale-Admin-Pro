from datetime import datetime, timedelta
from flask_login import current_user, login_required
import requests
from flask import Blueprint, render_template, request, session, make_response, g, redirect, url_for, jsonify, \
    current_app

from .database import DatabaseManager,ResponseResult
from exts import db

bp = Blueprint("preauthkey", __name__, url_prefix='/api/preauthkey')




@bp.route('/getPreAuthKey')
@login_required
def getPreAuthKey():
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    return DatabaseManager(db).get_pre_auth_key(current_user=current_user, page=page, per_page=per_page).to_dict()

@bp.route('/addKey', methods=['GET','POST'])
@login_required
def addKey():
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
    data = {'user':user_name,'reusable':True,'ephemeral':False,'expiration':expire_date.isoformat() + 'Z'}
    response = requests.post(url, headers=headers, json=data)
    return ResponseResult(
            code="0",
            msg="获取成功",
            count=0,  # 总记录数
            data=response.text,
            totalRow={}  # 当前页的记录数
        ).to_dict()
