import json
from flask_login import login_required, current_user
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
from utils import reload_headscale, to_rewrite_acl, table_res, res, is_user_mode


bp = Blueprint("acl", __name__, url_prefix='/api/acl')



@bp.route('/getACL')
@login_required
@role_required("manager")
def getACL():
    """获取所有 ACL 规则（全局 + 各用户）"""
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        base_query = """
            SELECT
                acl.id,
                acl.acl,
                acl.user_id,
                users.name as user_name
            FROM acl
            LEFT JOIN users ON acl.user_id = users.id
        """
        if is_user_mode():
            base_query += " WHERE acl.user_id = ? OR acl.user_id = 0"
            params = (current_user.id,)
        else:
            params = ()

        # 总数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']

        # 分页
        paginated_query = f"{base_query} ORDER BY acl.id DESC LIMIT ? OFFSET ?"
        paginated_params = params + (per_page, offset)
        cursor.execute(paginated_query, paginated_params)
        acls = cursor.fetchall()

    acls_list = []
    for acl in acls:
        acls_list.append({
            'id': acl['id'],
            'acl': acl['acl'],
            'user_id': acl['user_id'] or 0,
            'userName': acl['user_name'] if acl['user_id'] else '全局',
        })

    return table_res('0', '获取成功', acls_list, total_count, len(acls_list))



@bp.route('/re_acl', methods=['POST'])
@login_required
@role_required("manager")
def re_acl():
    """更新单条 ACL 规则"""
    acl_id = request.form.get('aclId')
    new_acl = request.form.get('newAcl')

    if not acl_id or not new_acl:
        return res('1', '缺少参数')

    try:
        json.loads(new_acl)
    except json.JSONDecodeError:
        return res('1', 'JSON 解析错误 — 请检查语法')

    with SqliteDB() as cursor:
        cursor.execute("UPDATE acl SET acl = ? WHERE id = ?", (new_acl, acl_id))

    return res('0', '更新成功')


@bp.route('/add_acl', methods=['POST'])
@login_required
@role_required("manager")
def add_acl():
    """新增全局 ACL 规则"""
    acl_json = request.form.get('acl')

    if not acl_json:
        return res('1', '缺少 ACL 内容')

    try:
        parsed = json.loads(acl_json)
    except json.JSONDecodeError:
        return res('1', 'JSON 解析错误 — 请检查语法')

    # 必须包含 action 字段
    if 'action' not in parsed:
        return res('1', 'ACL 规则必须包含 action 字段（accept/deny）')

    # user_id=0 表示全局规则
    with SqliteDB() as cursor:
        cursor.execute(
            "INSERT INTO acl (acl, user_id) VALUES (?, 0)",
            (json.dumps(parsed, ensure_ascii=False),)
        )

    return res('0', '添加成功')


@bp.route('/delete_acl', methods=['POST'])
@login_required
@role_required("manager")
def delete_acl():
    """删除 ACL 规则"""
    acl_id = request.form.get('aclId')

    if not acl_id:
        return res('1', '缺少 aclId')

    with SqliteDB() as cursor:
        cursor.execute("DELETE FROM acl WHERE id = ?", (acl_id,))

    return res('0', '删除成功')


@bp.route('/rewrite_acl', methods=['POST'])
@login_required
@role_required("manager")
def rewrite_acl():
    """将所有 ACL 规则写入 headscale 策略文件并重载"""
    result = to_rewrite_acl()
    if result['code'] == '0':
        # 写入后自动重载
        reload_headscale()
    return result


@bp.route('/read_acl', methods=['POST'])
@login_required
@role_required("manager")
def read_acl():
    """读取当前生效的 headscale ACL 文件"""
    acl_path = "/etc/headscale/acl.hujson"
    try:
        with open(acl_path, 'r') as f:
            acl_data = json.load(f)
    except FileNotFoundError:
        return res('1', f"文件 {acl_path} 未找到")
    except json.JSONDecodeError:
        return res('2', "无法解析 ACL 文件中的 JSON")
    except Exception as e:
        return res('3', f"发生未知错误: {str(e)}")

    rows = []
    for acl in acl_data.get('acls', []):
        action = acl.get('action', '')
        src = ', '.join(acl.get('src', []))
        dst = ', '.join(acl.get('dst', []))
        rows.append(
            f"<tr>"
            f"<td style='width:60px;text-align:center'>{action}</td>"
            f"<td style='padding-left:10px'>{src}</td>"
            f"<td style='padding-left:10px'>{dst}</td>"
            f"</tr>"
        )

    top_note = ""
    if acl_data.get('randomizeClientPort') is not None:
        rcp = acl_data['randomizeClientPort']
        top_note = f"<p style='margin:8px 12px;color:#666'>randomizeClientPort: {rcp} ｜ 路由隔离: per-user primary routes</p>"

    html = (
        f"<div>{top_note}"
        f"<table border='1' style='margin:10px'>"
        f"<tr><th>Action</th><th>Source</th><th>Destination</th></tr>"
        f"{''.join(rows)}"
        f"</table></div>"
    )
    return res('0', '读取成功', html)


@bp.route('/reload', methods=['POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()
