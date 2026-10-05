from flask import Flask, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from login_setup import init_login_manager
from utils import get_data_record, start_headscale, to_init_db, get_headscale_version, get_headscale_version_line
import config_loader,os


# 导入蓝图
from blueprints.auth import bp as auth_bp
from blueprints.admin import bp as admin_bp
from blueprints.user import bp as user_bp
from blueprints.node import bp as node_bp
from blueprints.system import bp as system_bp
from blueprints.route import bp as route_bp
from blueprints.acl import bp as acl_bp
from blueprints.preauthkey import bp as preauthkey_bp
from blueprints.log import bp as log_bp
from blueprints.set import bp as set_bp

# 创建 Flask 应用实例
app = Flask(__name__)

# 应用配置
app.config.from_object(config_loader)
app.json.ensure_ascii = False  # 让接口返回的中文不转码

# 信任反向代理的 X-Forwarded-For 和 X-Forwarded-Proto（不信任 X-Forwarded-Host，避免被上游错误 Host 污染）
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0)

# 初始化 CSRF 保护
app.config['WTF_CSRF_SSL_STRICT'] = False  # 允许代理终止 HTTPS 后以 HTTP 转发
csrf = CSRFProtect(app)


# 初始化 Flask-login
init_login_manager(app)

# 创建蓝图列表
blueprints = [auth_bp,admin_bp,user_bp,node_bp,system_bp,route_bp,acl_bp,preauthkey_bp,log_bp,set_bp]

# 循环注册蓝图
for blueprint in blueprints:
    app.register_blueprint(blueprint)


#启动 headscale
start_headscale()
to_init_db(app)

# 版本号在启动时查一次进 utils 的缓存（`headscale version` 不依赖 serve 进程）。
# 首页、设置页、关于弹窗原先各 fork 一次子进程，现在都读这份缓存。
get_headscale_version()


#定义一个定时任务函数，每个一个小时记录一下流量使用情况
def my_task():
    with app.app_context():
        return get_data_record()


# 创建调度
scheduler = BackgroundScheduler()
# 添加任务，每隔 1 Hour 执行一次
scheduler.add_job(func=my_task, trigger='interval', seconds=3600)
# 启动调度器
scheduler.start()


# 「关于」弹窗的内容。
#
# 这里以前是 static/views/system/about.html —— 一个静态文件，版本号写死在里面，
# 于是面板升级后它一直显示旧版本。layui 的 view.render() 是 $.ajax 取回 HTML
# 后原样注入（只从里面抠 <title>），所以这个 URL 交给 Flask 渲染就能拿到真实版本。
#
# 路由必须挂在 app 上而不是 admin 蓝图里：蓝图的 url_prefix 是 /admin，而 layui
# 按 config.js 的 views 路径请求 /static/views/system/about.html。这条规则不带
# 任何参数，Werkzeug 排序时优先于 Flask 内置的 /static/<path:filename>，因此能
# 覆盖掉那个静态文件 —— 静态文件本身已删除，避免出现第二份版本号。
@app.route('/static/views/system/about.html')
def about_view():
    return render_template('admin/about.html', hs_version=get_headscale_version_line())


# 自定义404错误处理器
@app.errorhandler(404)
def page_not_found(e):
    return render_template('auth/error.html', message="404")

# 仅在页面请求时设置 CSRF cookie，跳过静态资源以减少开销
@app.after_request
def set_csrf_cookie(response):
    if request.method == 'GET' and not request.path.startswith('/static/'):
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        response.set_cookie(
            'csrf_token', token,
            httponly=False,
            samesite='Lax',
            secure=app.config.get('SESSION_COOKIE_SECURE', False),
        )
    return response

# CSRF / 400 错误处理器（返回 JSON，兼容 AJAX 前端）
@app.errorhandler(400)
def bad_request(e):
    return {'code': '1', 'msg': '请求无效或 CSRF 验证失败', 'data': ''}, 400

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    if debug_mode:
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        from waitress import serve
        serve(app, host="0.0.0.0", port=5000)