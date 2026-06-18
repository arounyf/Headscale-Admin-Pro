import json
from flask_login import login_required, current_user
from login_setup import role_required
from flask import Blueprint, request
from utils import reload_headscale, res

bp = Blueprint("acl", __name__, url_prefix='/api/acl')

ACL_PATH = "/etc/headscale/acl.hujson"

DEFAULT_ACL = {
    "randomizeClientPort": False,
    "acls": [
        {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]},
        {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:internet:*"]},
    ],
}


@bp.route('/get_acl', methods=['GET', 'POST'])
@login_required
@role_required("manager")
def get_acl():
    """读取当前 ACL 文件返回完整 JSON"""
    try:
        with open(ACL_PATH, 'r') as f:
            acl_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        acl_data = DEFAULT_ACL

    return res('0', '', json.dumps(acl_data, indent=4, ensure_ascii=False))


@bp.route('/save_acl', methods=['POST'])
@login_required
@role_required("manager")
def save_acl():
    """保存 ACL JSON 到文件并重载"""
    raw = request.form.get('acl', '')

    if not raw.strip():
        return res('1', 'ACL 内容为空')

    try:
        acl_data = json.loads(raw)
    except json.JSONDecodeError as e:
        return res('1', f'JSON 解析错误: {e}')

    if 'acls' not in acl_data:
        return res('1', "必须包含 'acls' 字段")

    for i, acl in enumerate(acl_data['acls']):
        if 'action' not in acl:
            return res('1', f"第 {i+1} 条规则缺少 'action' 字段")

    try:
        with open(ACL_PATH, 'w') as f:
            json.dump(acl_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        return res('1', f'写入文件失败: {e}')

    reload_headscale()
    return res('0', '保存成功，headscale 已重载')


@bp.route('/reload', methods=['POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()
