
from flask_login import login_required, current_user
from login_setup import role_required
from flask import Blueprint, render_template, current_app, request
from utils import get_server_net, get_headscale_pid, get_headscale_version

bp = Blueprint("admin", __name__, url_prefix='/admin')




@bp.route('/')
@login_required
def admin():
    # 定义每个菜单项及其对应的可访问角色

    menu_items = {
        'console': {'html': '<dd data-name="console" class="layui-this"><a lay-href="console"><i class="layui-icon layui-icon-console"></i>控制台</a></dd>', 'roles': ['manager']},
        'user': {'html': '<dd data-name="console"><a lay-href="user"><i class="layui-icon layui-icon-user"></i>用户</a></dd>', 'roles': ['manager']},
        'node': {'html': '<dd data-name="console"><a lay-href="node"><i class="layui-icon layui-icon-website"></i>节点</a></dd>', 'roles': ['manager', 'user']},
        'route': {'html': '<dd data-name="console"><a lay-href="route"><i class="layui-icon layui-icon-senior"></i>路由</a></dd>', 'roles': ['manager', 'user']},
        'deploy': {'html': '<dd data-name="console"><a lay-href="deploy"><i class="layui-icon layui-icon-chat"></i>指令</a></dd>', 'roles': ['manager', 'user']},
        'help': {'html': '<dd data-name="console"><a lay-href="help"><i class="layui-icon layui-icon-read"></i>文档</a></dd>', 'roles': ['manager', 'user']},
        'acl': {'html': '<dd data-name="console"><a lay-href="acl"><i class="layui-icon layui-icon-auz"></i>ACL</a></dd>', 'roles': ['manager']},
        'preauthkey': {'html': '<dd data-name="console"><a lay-href="preauthkey"><i class="layui-icon layui-icon-key"></i>密钥</a></dd>', 'roles': ['manager', 'user']},
        'set': {'html': '<dd data-name="console"><a lay-href="set"><i class="layui-icon layui-icon-set"></i>设置</a></dd>', 'roles': ['manager']},
        'log': {'html': '<dd data-name="console"><a lay-href="log"><i class="layui-icon layui-icon-form"></i>日志</a></dd>', 'roles': ['manager', 'user']}
    }


    role = current_user.role
    print(role)
    if(role == "manager"):
        default_page = "console"
    else:
        default_page = "node"
    menu_html = "".join(item['html'] for item in menu_items.values() if role in item['roles'])

    return render_template('admin/index.html', menu_html=menu_html,default_page=default_page)



@bp.route('/console')
@login_required
@role_required("manager")
def console():
    region_html = current_app.config['REGION_HTML']
    return render_template('admin/console.html',region_html = region_html)



@bp.route('/user')
@login_required
@role_required("manager")
def user():
    return render_template('admin/user.html')




@login_required
@bp.route('/node')
def node():
    print(request.url)
    return render_template('admin/node.html')

@login_required
@bp.route('/route')
def route():
    return render_template('admin/route.html')

@login_required
@bp.route('/deploy')
def deploy():
    server_url = current_app.config['SERVER_URL']
    return render_template('admin/deploy.html',server_url = server_url)

@login_required
@bp.route('/help')
def help():
    return render_template('admin/help.html')



@bp.route('/acl')
@login_required
@role_required("manager")
def acl():
    return render_template('admin/acl.html')

@login_required
@bp.route('preauthkey')
def preauthkey():
    return render_template('admin/preauthkey.html')

@login_required
@bp.route('log')
def log():
    return render_template('admin/log.html')

@login_required
@bp.route('info')
def info():
    return render_template('admin/info.html')



@login_required
@bp.route('set')
def set():
    apikey = current_app.config['BEARER_TOKEN']
    server_url = current_app.config['SERVER_URL']
    server_net = current_app.config['SERVER_NET']

    options_html = ""
    for interface in get_server_net()["network_interfaces"]:
        if interface == server_net:
            options_html += f'<option value="{interface}" selected>{interface}</option>\n'
        else:
            options_html += f'<option value="{interface}">{interface}</option>\n'

    region_html = current_app.config['REGION_HTML']


    print(get_headscale_pid())
    if get_headscale_pid():
        headscale_status = "checked"
    else:
        headscale_status = ""

    return render_template('admin/set.html',apikey = apikey,server_url = server_url,server_net = options_html,region_html = region_html,headscale_status = headscale_status,version = get_headscale_version())


@login_required
@bp.route('password')
def password():
    return render_template('admin/password.html')


