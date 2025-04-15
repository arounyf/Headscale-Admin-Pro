from flask_login import login_required, current_user
from sqlalchemy import func
from models import UserModel,  PreAuthKeysModel, LogModel
from flask import Blueprint,  request

bp = Blueprint("log", __name__, url_prefix='/api/log')


res_json = {'code': '', 'data': '', 'msg': ''}

@bp.route('/getLogs')
@login_required
def getLogs():
    # 分页查询
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条


    # 使用 func.strftime 格式化时间字段
    query = LogModel.query.with_entities(
        LogModel.id,
        LogModel.content,
        UserModel.name,
        func.strftime('%Y-%m-%d %H:%M:%S', LogModel.created_at,'localtime').label('created_at'),
        # 可以添加其他需要的字段
    ) .join(UserModel, LogModel.user_id == UserModel.id)

    # 判断用户角色
    if current_user.role != 'manager':
        # 如果不是 manager，只查询当前用户的节点信息
        query = query.filter(LogModel.user_id == current_user.id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # 数据格式化
    logs_list = [{
        'id': log.id,
        'content': log.content,
        'name': log.name,
        'create_time': log.created_at,

    } for log in logs]

    print("----------------------------------------------")
    print(logs)
    # 接口返回json数据
    res_json = {
        'code': '0',
        'data': logs_list,
        'msg': '获取成功',
        'count': pagination.total,
        'totalRow': {
            'count': len(logs)
        }
    }

    return res_json
