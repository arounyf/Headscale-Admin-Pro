from flask import Flask, render_template
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler

import config_loader
from exts import db, enable_sqlite_foreign_keys
from login_setup import init_login_manager
from utils import get_data_record, start_headscale

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


# 初始化数据库
db.init_app(app)
# 在应用上下文里绑定事件监听器
with app.app_context():
    enable_sqlite_foreign_keys(db.engine)


# 初始化 Flask-login
init_login_manager(app)


# 初始化数据库迁移
migrate = Migrate(app, db)


# 创建蓝图列表
blueprints = [auth_bp,admin_bp,user_bp,node_bp,system_bp,route_bp,acl_bp,preauthkey_bp,log_bp,set_bp]
# 循环注册蓝图
for blueprint in blueprints:
    app.register_blueprint(blueprint)



# 定义一个定时任务函数，每个一个小时记录一下流量使用情况
def my_task():
    with app.app_context():
        return get_data_record()

# 创建调度
scheduler = BackgroundScheduler()
# 添加任务，每隔 10 秒执行一次
scheduler.add_job(func=my_task, trigger='interval', seconds=3600)
# 启动调度器
scheduler.start()

# 启动 headscale
start_headscale()


# 自定义404错误处理器
@app.errorhandler(404)
def page_not_found(e):
    return render_template('auth/error.html', message="404")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
