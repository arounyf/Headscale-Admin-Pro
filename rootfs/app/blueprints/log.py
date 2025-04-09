from flask_login import login_required, current_user
from flask import Blueprint,  request
from .database import DatabaseManager
from exts import db
bp = Blueprint("log", __name__, url_prefix='/api/log')


@bp.route('/getLogs')
@login_required
def getLogs():
    # 分页查询
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    return  DatabaseManager(db).getLogPagination(current_user,page,per_page).to_dict()

     
