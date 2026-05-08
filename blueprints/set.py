import subprocess
from flask_login import login_required
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request, current_app, session
from utils import start_headscale, stop_headscale, save_config_yaml, res


bp = Blueprint("set", __name__, url_prefix='/api/set')




@bp.route('/upset' , methods=['GET','POST'])
@login_required
@role_required("manager")
def upset():
    form_fields = {
        'BEARER_TOKEN': 'apiKey',
        'SERVER_NET': 'serverNet',
        'SERVER_URL': 'serverUrl',
        'DEFAULT_NODE_COUNT': 'defaultNodeCount',
        'OPEN_USER_REG': 'openUserReg',
        'DEFAULT_REG_DAYS': 'defaultRegDays',
        'SMTP_HOST': 'smtpHost',
        'SMTP_PORT': 'smtpPort',
        'SMTP_USER': 'smtpUser',
        'SMTP_PASSWORD': 'smtpPassword',
        'SMTP_FROM': 'smtpFrom',
        'SMTP_FROM_NAME': 'smtpFromName',
        'SMTP_SSL': 'smtpSsl',
        'EMAIL_VERIFY_REG': 'emailVerifyReg',
        'TIANAPI_KEY': 'tianapiKey',
    }
    # 构建反向映射：form字段名 -> config key
    form_to_config = {v: k for k, v in form_fields.items()}

    config_mapping = {}
    for key, value in request.form.items():
        config_key = key if key in form_fields else form_to_config.get(key)
        if config_key:
            config_mapping[config_key] = value

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


@bp.route('/user_mode', methods=['POST'])
@login_required
@role_required("manager")
def user_mode():
    mode = request.form.get('mode', 'admin')
    session['user_mode'] = mode if mode in ('admin', 'user') else 'admin'
    return res('0', f'已切换到{"用户" if mode == "user" else "管理员"}模式', '')

