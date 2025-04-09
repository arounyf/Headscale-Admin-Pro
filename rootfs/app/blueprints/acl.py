import json
from flask_login import login_required
from exts import db
from login_setup import role_required
from models import ACLModel
from flask import Blueprint,  request
from utils import reload_headscale,fecth_headscale,set_headscale
from .database import DatabaseManager,ResponseResult

bp = Blueprint("acl", __name__, url_prefix='/api/acl')




@bp.route('/getACL')
@login_required
@role_required("manager")
def getACL():
    page = request.args.get('page', default=1, type=int)  # 默认第 1 页
    per_page = request.args.get('limit', default=10, type=int)  # 默认每页 10 条
    response = DatabaseManager(db).get_acl(page=page, per_page=per_page) 
    return response.to_dict()
     


@bp.route('/re_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def re_acl():
    acl_id = request.form.get('aclId')
    new_acl = request.form.get('newAcl')
    try:
        json.loads(new_acl)
    except json.JSONDecodeError:
        return ResponseResult(
            code="1",
            msg="解析错误",
            count=0,
            data=[],
            totalRow={}
        ).to_dict()
    DatabaseManager(db).re_acl(acl_id,new_acl)
    return ResponseResult(
            code="0",
            msg="更新成功",
            count=0,
            data=[],
            totalRow={}
        ).to_dict()


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
    try:
        with open(acl_path, 'w') as f:
            json.dump(acl_data, f, indent=4)
    except Exception as e:
        return ResponseResult(
            code="1",
            msg="写入失败",
            count=0,
            data=str(e),
            totalRow={}
        ).to_dict()
    return ResponseResult(
            code="0",
            msg="写入成功",
            count=0,
            data=acl_data,
            totalRow={}
        ).to_dict()


@bp.route('/read_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def read_acl():
    acl_data=fecth_headscale()
    if acl_data is None:
        return ResponseResult(
            code="1",
            msg="获取失败",
            count=0,
            data="",
            totalRow={}
        ).to_dict() 
    html_content = "<table border='1' style='margin:10px;'>"
    html_content += "<tr><th>Action</th><th>Source</th><th>Destination</th></tr>"
    for item in acl_data.get('acls',{}):
        action = item['action']
        src = ', '.join(item['src'])
        dst = ', '.join(item['dst'])
        html_content += f"<tr><td  style='width:60px;text-align:center'>{action}</td><td  style='padding-left:10px;'>{src}</td><td  style='padding-left:10px;'>{dst}</td></tr>"

    html_content += "</table>"

    return ResponseResult(
            code="0",
            msg="读取成功",
            count=0,
            data=html_content,
            totalRow={}
        ).to_dict()



@bp.route('/reload', methods=['GET','POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()