import subprocess
from flask_login import login_required
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request, current_app
from utils import start_headscale, stop_headscale, save_config_yaml, res


bp = Blueprint("set", __name__, url_prefix='/api/set')




@bp.route('/upset' , methods=['GET','POST'])
@login_required
@role_required("manager")
def upset():
    # 反转 form_fields 字典的键值对
    form_fields = {
        'BEARER_TOKEN': 'apiKey',
        'SERVER_NET': 'serverNet',
        'SERVER_URL':'serverUrl',
        'DEFAULT_NODE_COUNT': 'defaultNodeCount',
        'OPEN_USER_REG': 'openUserReg',
        'DEFAULT_REG_DAYS': 'defaultRegDays',
    }

    # 构建字典
    config_mapping = {}

    for config_key, form_value in form_fields.items():
        value = request.form.get(form_value)
    return save_config_yaml(config_mapping)


@bp.route('/get_apikey' , methods=['POST'])
@login_required
@role_required("manager")
def get_apikey():
    with SqliteDB() as cursor:
        try:
            # 删除所有记录
            delete_query = "DELETE FROM api_keys;"
            cursor.execute(delete_query)
            num_rows_deleted = cursor.rowcount
            print(f"成功删除 {num_rows_deleted} 条记录")
        except Exception as e:
            print(f"删除记录时出现错误: {e}")
            return res('1', f"删除记录时出现错误: {e}", '')

    try:
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)
        return res('0', '执行成功', result.stdout)
    except subprocess.CalledProcessError as e:
        return res('1', '执行失败', f"错误信息：{e.stderr}")



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

