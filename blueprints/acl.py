import json
from flask_login import login_required
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request
from utils import reload_headscale, to_rewrite_acl, table_res, res


bp = Blueprint("acl", __name__, url_prefix='/api/acl')



@bp.route('/getACL')
@login_required
@role_required("manager")
def getACL():
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('limit', default=10, type=int)
    offset = (page - 1) * per_page

    with SqliteDB() as cursor:
        # 构建基础查询语句
        base_query = """
            SELECT 
                acl.id,
                acl.acl,
                users.name
            FROM 
                acl acl
            JOIN 
                users ON acl.user_id = users.id
        """

        # 查询总记录数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        cursor.execute(count_query)
        total_count = cursor.fetchone()['total']

        # 分页查询
        paginated_query = f"{base_query} LIMIT? OFFSET? "
        paginated_params = (per_page, offset)
        cursor.execute(paginated_query, paginated_params)
        acls = cursor.fetchall()

    # 数据格式化
    acls_list = []
    for acl in acls:
        acls_list.append({
            'id': acl['id'],
            'acl': acl['acl'],
            'userName': acl['name']
        })



    return table_res('0', '获取成功',acls_list,total_count,len(acls_list))



@bp.route('/re_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def re_acl():
    acl_id = request.form.get('aclId')
    new_acl = request.form.get('newAcl')


    try:
        json.loads(new_acl)
    except json.JSONDecodeError:
        return res('1', '解析错误')


    with SqliteDB() as cursor:
        # 更新 ACL 记录
        update_query = "UPDATE acl SET acl =? WHERE id =?;"
        cursor.execute(update_query, (new_acl, acl_id))


    return res('0','更新成功')



@bp.route('/rewrite_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def rewrite_acl():
    return  to_rewrite_acl()


@bp.route('/read_acl', methods=['GET','POST'])
@login_required
@role_required("manager")
def read_acl():
    acl_path = "/etc/headscale/acl.hujson"
    try:
        with open(acl_path, 'r') as f:
            acl_data = json.load(f)

    except FileNotFoundError:
        return res('1', f"错误: 文件 {acl_path} 未找到。")
    except json.JSONDecodeError:
        return res('2', f"错误: 无法解析 {acl_path} 中的 JSON 数据。")
    except Exception as e:
        return res( '3', f"发生未知错误: {str(e)}")


    print(acl_data.get('acls', []))

    html_content = "<table border='1' style='margin:10px;'>"
    html_content += "<tr><th>Action</th><th>Source</th><th>Destination</th></tr>"

    for item in acl_data.get('acls', []):
        action = item['action']
        src = ', '.join(item['src'])
        dst = ', '.join(item['dst'])
        html_content += f"<tr><td  style='width:60px;text-align:center'>{action}</td><td  style='padding-left:10px;'>{src}</td><td  style='padding-left:10px;'>{dst}</td></tr>"

    html_content += "</table>"

    return res('0','读取成功',html_content)



@bp.route('/reload', methods=['GET','POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()