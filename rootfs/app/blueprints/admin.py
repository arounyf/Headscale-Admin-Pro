from flask_login import login_required, current_user
from login_setup import role_required
from models import UserModel
from flask import Blueprint, render_template, request, session, make_response, g, redirect, url_for, current_app
from .forms import RegisterForm, LoginForm
from blueprints.forms import RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
from .get_captcha import get_captcha_code_and_content
bp = Blueprint("admin", __name__, url_prefix='/admin')




@bp.route('/')
@login_required
def admin(default_page=None):
    # 定义每个菜单项及其对应的可访问角色

    menu_items = {
        'console': {'html': '<dd data-name="console"><a lay-href="console">控制台</a></dd>', 'roles': ['manager']},
        'user': {'html': '<dd data-name="user"><a lay-href="user">用户</a></dd>', 'roles': ['manager']},
        'node': {'html': '<dd data-name="node"><a lay-href="node">节点</a></dd>', 'roles': ['manager', 'user']},
        'route': {'html': '<dd data-name="route"><a lay-href="route">路由</a></dd>', 'roles': ['manager', 'user']},
        'deploy': {'html': '<dd data-name="deploy"><a lay-href="deploy">指令</a></dd>', 'roles': ['manager', 'user']},
        'help': {'html': '<dd data-name="help"><a lay-href="help">文档</a></dd>', 'roles': ['manager', 'user']},
        'acl': {'html': '<dd data-name="acl"><a lay-href="acl">ACL</a></dd>', 'roles': ['manager']},
        'preauthkey': {'html': '<dd data-name="preauthkey"><a lay-href="preauthkey">密钥</a></dd>', 'roles': ['manager', 'user']},
        'log': {'html': '<dd data-name="log"><a lay-href="log">日志</a></dd>', 'roles': ['manager', 'user']}
    }

    # 获取当前用户角色
    role = current_user.role
    print(role)

    # 如果没有传递 default_page 参数，则根据角色设置默认值
    if not default_page:
        default_page = "console" if role == "manager" else "node"
    # 动态生成菜单 HTML，设置 class="layui-this" 给 default_page
    # 动态生成菜单 HTML，并为 default_page 的 dd 标签加上 class="layui-this"
    menu_html = ""
    for key, item in menu_items.items():
        if role in item['roles']:
            if key == default_page:
                # 添加 layui-this 类到指定的 default_page
                modified_html = item['html'].replace('<dd ', '<dd class="layui-this ')
            else:
                modified_html = item['html']
            menu_html += modified_html
    console.log("---------------------------------")
    console.log(default_page)
    console.log(menu_html)
    return render_template('admin/index.html', menu_html=menu_html,default_page=default_page)



@bp.route('/console')
@login_required
@role_required("manager")
def console():
    region = current_app.config['REGION']
    return render_template('admin/console.html',region = region)



@bp.route('/user')
@login_required
@role_required("manager")
def user():
    return render_template('admin/user.html')




@login_required
@bp.route('/node')
def node():
    return render_template('admin/node.html')

@login_required
@bp.route('/route')
def route():
    return render_template('admin/route.html')

@login_required
@bp.route('/deploy')
def deploy():
    tailscale_up_url = current_app.config['TAILSCALE_UP_URL']
    return render_template('admin/deploy.html',tailscale_up_url = tailscale_up_url)

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
@bp.route('password')
def password():
    return render_template('admin/password.html')


