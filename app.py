from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from login_setup import init_login_manager
from utils import get_data_record, start_headscale, to_init_db
import config_loader
from werkzeug.middleware.proxy_fix import ProxyFix  # 导入中间件 解决https带端口登录跳转问题

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
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)   # 解决https带端口登录跳转问题
app.config['USE_X_FORWARDED_PROTO'] = True   # 解决https带端口登录跳转问题

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


# 自定义404错误处理器
@app.errorhandler(404)
def page_not_found(e):
    return render_template('auth/error.html', message="404")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
