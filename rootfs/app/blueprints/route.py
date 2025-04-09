from flask_login import login_required, current_user
import requests
from flask import Blueprint,  request, current_app
from .database import DatabaseManager,ResponseResult
from exts import db

bp = Blueprint("route", __name__, url_prefix='/api/route')



@bp.route('/getRoute')
@login_required
def getRoute():
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    return DatabaseManager(db).getRoute(current_user,page, per_page).to_dict()


@bp.route('/route_enable', methods=['GET','POST'])
@login_required
def route_enable():
    route_id = request.form.get('routeId')
    enabled = request.form.get('Enable')
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }

    if (enabled == "true"):
        msg = '打开成功'
        url = f'{server_host}/api/v1/routes/{route_id}/enable'  # 替换为实际的目标 URL
    else:
        msg = '关闭成功'
        url = f'{server_host}/api/v1/routes/{route_id}/disable'  # 替换为实际的目标 URL

    response = requests.post(url, headers=headers)
    return ResponseResult(
            code="0",
            msg="获取成功",
            count=0,  # 总记录数
            data=str(response.text),
            totalRow={}  # 当前页的记录数
        ).to_dict()

