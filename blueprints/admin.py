from flask_login import login_required, current_user
from login_setup import role_required
from flask import Blueprint, render_template, current_app, request, json
from utils import get_server_net, get_headscale_pid, get_headscale_version



bp = Blueprint("admin", __name__, url_prefix='/admin')




@bp.route('/')
@login_required
def admin():
    # 定义菜单项及其对应的可访问角色
    # icon: SVG 内联图标
    _svg = {
        'console': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M8 21h8m-4-4v4"/></svg>',
        'user': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>',
        'node': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/></svg>',
        'route': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
        'acl': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',
        'preauthkey': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>',
        'deploy': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>',
        'help': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>',
        'set': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
        'log': '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>',
    }
    menu_items = [
        {'name': '控制台', 'url': 'console', 'icon': _svg['console'], 'roles': ['manager']},
        {'name': '用户', 'url': 'user', 'icon': _svg['user'], 'roles': ['manager']},
        {'name': '节点', 'url': 'node', 'icon': _svg['node'], 'roles': ['manager', 'user']},
        {'name': '路由', 'url': 'route', 'icon': _svg['route'], 'roles': ['manager', 'user']},
        {'name': 'ACL', 'url': 'acl', 'icon': _svg['acl'], 'roles': ['manager']},
        {'name': '密钥', 'url': 'preauthkey', 'icon': _svg['preauthkey'], 'roles': ['manager', 'user']},
        {'name': '指令', 'url': 'deploy', 'icon': _svg['deploy'], 'roles': ['manager', 'user']},
        {'name': '文档', 'url': 'help', 'icon': _svg['help'], 'roles': ['manager', 'user']},
        {'name': '设置', 'url': 'set', 'icon': _svg['set'], 'roles': ['manager']},
        {'name': '日志', 'url': 'log', 'icon': _svg['log'], 'roles': ['manager', 'user']},
    ]

    role = current_user.role
    default_page = "console" if role == "manager" else "node"
    visible_menus = [m for m in menu_items if role in m['roles']]
    hs_running = 'running' if get_headscale_pid() else 'stopped'
    return render_template('admin/index.html', menu_items=visible_menus, default_page=default_page, hs_running=hs_running)



@bp.route('/console')
@login_required
@role_required("manager")
def console():
    return render_template('admin/console.html')



@bp.route('/user')
@login_required
@role_required("manager")
def user():
    return render_template('admin/user.html')





@bp.route('/node')
@login_required
def node():
    print(request.url)
    return render_template('admin/node.html',current_user=current_user )


@bp.route('/route')
@login_required
def route():
    return render_template('admin/route.html')


@bp.route('/deploy')
@login_required
def deploy():
    server_url = current_app.config['SERVER_URL']
    return render_template('admin/deploy.html',server_url = server_url)


@bp.route('/help')
@login_required
def help():
    return render_template('admin/help.html')



@bp.route('/acl')
@login_required
@role_required("manager")
def acl():
    return render_template('admin/acl.html')


@bp.route('preauthkey')
@login_required
def preauthkey():
    return render_template('admin/preauthkey.html')


@bp.route('log')
@login_required
def log():
    return render_template('admin/log.html')


@bp.route('info')
@login_required
def info():
    name = current_user.name
    cellphone = current_user.cellphone
    email = current_user.email
    node = current_user.node
    route = current_user.route
    expire = current_user.expire

    if (route == "1"):
        route = "checked"
    else:
        route = ""

    return render_template('admin/info.html', name = name,
                            cellphone = cellphone,
                            email = email,
                            node = node,
                            route = route,
                            expire = expire
                           )




@bp.route('set')
@login_required
def set():
    apikey = current_app.config['BEARER_TOKEN']
    server_url = current_app.config['SERVER_URL']
    server_net = current_app.config['SERVER_NET']
    default_reg_days = current_app.config['DEFAULT_REG_DAYS']
    default_node_count = current_app.config['DEFAULT_NODE_COUNT']
    open_user_reg = current_app.config['OPEN_USER_REG']

    options_html = ""
    for interface in get_server_net()["network_interfaces"]:
        if interface == server_net:
            options_html += f'<option value="{interface}" selected>{interface}</option>\n'
        else:
            options_html += f'<option value="{interface}">{interface}</option>\n'





    open_reg_checked = 'checked' if open_user_reg == 'on' else ''
    hs_status_checked = 'checked' if get_headscale_pid() else ''

    email_verify_reg = 'checked' if current_app.config.get('EMAIL_VERIFY_REG', 'off') == 'on' else ''
    smtp_ssl = 'checked' if str(current_app.config.get('SMTP_SSL', 'true')).lower() in ('true', '1', 'on') else ''

    return render_template('admin/set.html',apikey = apikey,
                               server_url = server_url,
                               server_net = options_html,
                               default_reg_days = default_reg_days,
                               default_node_count = default_node_count,
                               open_user_reg = open_reg_checked,
                               version = get_headscale_version(),
                               smtp_host = current_app.config.get('SMTP_HOST', ''),
                               smtp_port = current_app.config.get('SMTP_PORT', '465'),
                               smtp_user = current_app.config.get('SMTP_USER', ''),
                               smtp_password = current_app.config.get('SMTP_PASSWORD', ''),
                               smtp_from = current_app.config.get('SMTP_FROM', ''),
                               smtp_from_name = current_app.config.get('SMTP_FROM_NAME', ''),
                               smtp_ssl = smtp_ssl,
                               email_verify_reg = email_verify_reg,
                               headscale_status = hs_status_checked,
                           )



@bp.route('password')
@login_required
def password():
    return render_template('admin/password.html')


