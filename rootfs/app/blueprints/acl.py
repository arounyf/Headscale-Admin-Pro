import json
from flask_login import login_required
from exts import db
from login_setup import role_required
from models import UserModel,  ACLModel
from flask import Blueprint,  request
from utils import reload_headscale

bp = Blueprint("acl", __name__, url_prefix='/api/acl')


res_json = {'code': '', 'data': '', 'msg': ''}


@bp.route('/getACL')
@login_required
@role_required("manager")
def getACL():
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



@bp.route('/re_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def re_acl():
    acl_id = request.form.get('aclId')
    new_acl = request.form.get('newAcl')


    res_json['code'], res_json['msg'] = '0', '更新成功'
    try:
        json.loads(new_acl)
    except json.JSONDecodeError:
        res_json['code'], res_json['msg'] = '1', '解析错误'


    if (res_json['code'] == '0'):
        acl = ACLModel.query.filter_by(id=acl_id).first()
        acl.acl = new_acl
        db.session.commit()

    return res_json


@bp.route('/rewrite_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def rewrite_acl():

    acl_path="/etc/headscale/acl.hujson"
    acls = ACLModel.query.all()

    acl_list = [json.loads(acl.acl) for acl in acls]
    acl_data = {
        "acls": acl_list
    }
    print(acl_data)
    try:
        with open(acl_path, 'w') as f:
            json.dump(acl_data, f, indent=4)
        res_json['code'], res_json['msg'] = '0', '写入成功'
    except Exception as e:
        # return f"写入文件时出错: {str(e)}", 500
        res_json['code'], res_json['msg'] = '0', '写入失败'
        res_json['data'] = str(e)


    res_json['data'] = acl_data
    return  res_json


@bp.route('/read_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def read_acl():
    acl_path = "/etc/headscale/acl.hujson"
    try:
        with open(acl_path, 'r') as f:
            acl_data = json.load(f)

    except FileNotFoundError:
        res_json['code'], res_json['msg'] = '1', f"错误: 文件 {acl_path} 未找到。"
    except json.JSONDecodeError:
        res_json['code'], res_json['msg'] = '2', f"错误: 无法解析 {acl_path} 中的 JSON 数据。"
    except Exception as e:
        res_json['code'], res_json['msg'] = '3', f"发生未知错误: {str(e)}"


    print(acl_data.get('acls', []))

    html_content = "<table border='1' style='margin:10px;'>"
    html_content += "<tr><th>Action</th><th>Source</th><th>Destination</th></tr>"

    for item in acl_data.get('acls', []):
        action = item['action']
        src = ', '.join(item['src'])
        dst = ', '.join(item['dst'])
        html_content += f"<tr><td  style='width:60px;text-align:center'>{action}</td><td  style='padding-left:10px;'>{src}</td><td  style='padding-left:10px;'>{dst}</td></tr>"

    html_content += "</table>"

    print(html_content)
    res_json['data'] = html_content
    res_json['code'], res_json['msg'] = '0', '读取成功'

    return res_json



@bp.route('/reload', methods=['GET','POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()