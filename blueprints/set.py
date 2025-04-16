import json
from flask_login import login_required
from exts import db
from login_setup import role_required
from models import UserModel,  ACLModel
from flask import Blueprint,  request
from utils import reload_headscale

bp = Blueprint("set", __name__, url_prefix='/api/set')


res_json = {'code': '', 'data': '', 'msg': ''}


@bp.route('/getset')
@login_required
@role_required("manager")
def upset():
    # print(session)
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    #
    # 分页查询
    # 分页查询

    # 使用 func.strftime 格式化时间字段
    query = ACLModel.query.with_entities(
        ACLModel.id,
        ACLModel.acl,
        UserModel.name,
        # 可以添加其他需要的字段
    ) .join(UserModel, ACLModel.user_id == UserModel.id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    acls = pagination.items
    #
    # 数据格式化
    acls_list = [{
        'id': acl.id,
        'acl': acl.acl,
        'userName': acl.name,

    } for acl in acls]

    # 接口返回json数据
    res_json = {
        'code': '',
        'data': '',
        'msg': '',
        'count': pagination.total,
        'totalRow': {
            'count': len(acls)
        }
    }

    res_json['code'], res_json['msg'] = '0', '获取成功'
    res_json['data'] = acls_list


    return res_json


