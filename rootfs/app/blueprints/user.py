from datetime import datetime
from flask_login import current_user, login_required
from sqlalchemy import func
from exts import db
from login_setup import role_required
from models import UserModel
from flask import Blueprint, request
from werkzeug.security import check_password_hash
from .database import DatabaseManager,ResponseResult
from exts import db


bp = Blueprint("user", __name__, url_prefix='/api/user')


@bp.route('/getUsers')
@login_required
@role_required("manager")
def getUsers():
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    return DatabaseManager(db).getUserPagination(page=page, per_page=per_page).to_dict()
  


@bp.route('/re_expire',methods=['GET','POST'])
@login_required
@role_required("manager")
def re_expire():
    user_id = request.form.get('user_id')
    new_expire = datetime.strptime(request.form.get('new_expire'), '%Y-%m-%d %H:%M:%S')
    return DatabaseManager(db).updateUserExpire(user_id=user_id, new_expire=new_expire).to_dict()


@bp.route('/user_enable',methods=['GET','POST'])
@login_required
@role_required("manager")
def user_enable():
    user_id = request.form.get('user_id')
    enable = request.form.get('enable')
    return DatabaseManager(db).userEnable(user_id=user_id, enable=enable).to_dict()


@bp.route('/delUser',methods=['GET','POST'])
@login_required
@role_required("manager")
def delUser():
    user_id = request.form.get('user_id')
    return DatabaseManager(db).delUser(user_id=user_id).to_dict()

@bp.route('/init_data',methods=['GET'])
@login_required
def init_data():
    user_created_at = current_user.created_at
    user_expire = current_user.expire
    # 默认密码999888 进行判断 前端提示用户修改密码
    if check_password_hash(current_user.password, '999888'):
       defaultPass = '1'
    else:
       defaultPass = '0'
    data = {"created_at":str(user_created_at),"expire":str(user_expire),"defaultPass":defaultPass}
    return ResponseResult(
            code="0",
            msg="查询成功",
            count=0,
            data=data,
            totalRow={}
        ).to_dict() 


