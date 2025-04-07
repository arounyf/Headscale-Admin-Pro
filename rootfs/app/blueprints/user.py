from datetime import datetime
from flask_login import current_user, login_required
from sqlalchemy import func
from exts import db
from login_setup import role_required
from models import UserModel
from flask import Blueprint, request



bp = Blueprint("user", __name__, url_prefix='/api/user')

res_json = {'code': '', 'data': '', 'msg': ''}

@bp.route('/getUsers')
@login_required
@role_required("manager")
def getUsers():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条

    # 使用 func.strftime 格式化时间字段
    query = UserModel.query.with_entities(
        UserModel.id,
        UserModel.name,
        func.strftime('%Y-%m-%d %H:%M:%S', UserModel.created_at, ).label('created_at'),
        UserModel.cellphone,
        func.strftime('%Y-%m-%d %H:%M:%S', UserModel.expire, ).label('expire'),
        UserModel.enable,
        # 可以添加其他需要的字段
    )

    # 分页查询
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items



    # 数据格式化
    users_list = [{
        'id': user.id,
        'userName': user.name,
        'createTime':user.created_at,
        'cellphone':user.cellphone,
        'role':user.role,
        'expire':user.expire,
        'enable':user.enable,
    } for user in users]

    # 额外字段
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
        'count':pagination.total,
        'totalRow':{
                'count':len(users)
            }
    }
    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = users_list


    return res_json


@bp.route('/re_expire',methods=['GET','POST'])
@login_required
@role_required("manager")
def re_expire():
    user_id = request.form.get('user_id')
    new_expire = datetime.strptime(request.form.get('new_expire'), '%Y-%m-%d %H:%M:%S')
    print(new_expire)
    print(user_id)
    user = UserModel.query.filter_by(id=user_id).first()
    user.expire = new_expire
    db.session.commit()

    res_json['code'], res_json['msg'] = '0', '更新成功'
    return res_json


@bp.route('/user_enable',methods=['GET','POST'])
@login_required
@role_required("manager")
def user_enable():
    user_id = request.form.get('user_id')
    enable = request.form.get('enable')

    print(user_id)
    user = UserModel.query.filter_by(id=user_id).first()
    res_json['code']= '0'
    if (enable == "true"):
        user.enable = 1
        res_json['msg'] = ('启用成功')
    else:
        user.enable = 0
        res_json['msg'] = ('关闭成功')
    db.session.commit()

    return res_json


@bp.route('/delUser',methods=['GET','POST'])
@login_required
@role_required("manager")
def delUser():
    user_id = request.form.get('user_id')

    print(user_id)
    user = UserModel.query.filter_by(id=user_id).first()
    db.session.delete(user)
    db.session.commit()

    res_json['code'], res_json['msg'] = '0', '更新成功'
    return res_json

@bp.route('/init_data',methods=['GET'])
@login_required
def init_data():
    user_created_at = current_user.created_at
    user_expire = current_user.expire
    print(user_created_at)
    print(user_expire)

    data = {"created_at":str(user_created_at),"expire":str(user_expire)}

    res_json['code'], res_json['msg'] = '0', '查询成功'
    res_json['data'] = data
    print(res_json)
    return res_json


