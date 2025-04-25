import subprocess
from flask_login import login_required
from exts import db
from login_setup import role_required
from flask import Blueprint, request,current_app
from ruamel.yaml import YAML
from models import ApiKeys
from utils import start_headscale, stop_headscale, save_config_yaml

bp = Blueprint("set", __name__, url_prefix='/api/set')


res_json = {'code': '', 'data': '', 'msg': ''}


@bp.route('/upset' , methods=['GET','POST'])
@login_required
@role_required("manager")
def upset():
    apikey = request.form.get('apiKey')
    server_net = request.form.get('serverNet')
    server_url = request.form.get('serverUrl')
    region_html = request.form.get('regionHtml')
    region_data = request.form.get('regionData')
    default_node_count = request.form.get('defaultNodeCount')
    open_user_reg = request.form.get('openUserReg')
    default_reg_days = request.form.get('defaultRegDays')

    # 定义映射字典
    config_mapping = {
        'BEARER_TOKEN': apikey,
        'SERVER_URL': server_url,
        'SERVER_NET': server_net,
        'DEFAULT_NODE_COUNT': default_node_count,
        'OPEN_USER_REG': open_user_reg,
        'DEFAULT_REG_DAYS': default_reg_days,
        'REGION_HTML': region_html,
        'REGION_DATA': region_data
    }

    return save_config_yaml(config_mapping)



@bp.route('/get_apikey' , methods=['POST'])
@login_required
@role_required("manager")
def get_apikey():
    #获取之前先清理
    try:
        # 删除所有记录
        num_rows_deleted = ApiKeys.query.delete()
        # 提交事务
        db.session.commit()
        print(f"成功删除 {num_rows_deleted} 条记录")
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        print(f"删除记录时出现错误: {e}")

    try:
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)

        res_json['code'], res_json['msg'], res_json['data'] = '0', '执行成功', result.stdout
    except subprocess.CalledProcessError as e:
        res_json['code'], res_json['msg'], res_json['data'] = '1', '执行失败', f"错误信息：{e.stderr}"

    return res_json



@bp.route('/switch_headscale', methods=['POST'])
@login_required
@role_required("manager")
def switch_headscale():
    # 获取表单中的 Switch 参数
    status = request.form.get('Switch')
    res_json = {'code': '', 'data': '', 'msg': ''}
    if status=="true":
        return start_headscale()
    else:
        return stop_headscale()

    return res_json

