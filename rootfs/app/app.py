from flask import Flask,  render_template
import config, os
from exts import db, enable_sqlite_foreign_keys
from blueprints.auth import bp as auth_bp
from blueprints.admin import bp as admin_bp
from blueprints.user import bp as user_bp
from blueprints.node import bp as node_bp
from blueprints.node import bp_node as node_bp_node
from blueprints.system import bp as system_bp
from blueprints.route import bp as route_bp
from blueprints.acl import bp as acl_bp
from blueprints.preauthkey import bp as preauthkey_bp
from blueprints.log import bp as log_bp
from flask_migrate import Migrate
from login_setup import init_login_manager
from apscheduler.schedulers.background import BackgroundScheduler
from utils import  get_data_record

app= Flask(__name__)
app.config.from_object(config)
app.json.ensure_ascii = False  #让接口返回的中文不转码



# 初始化 Flask-login
init_login_manager(app)

db.init_app(app)
# 在应用上下文里绑定事件监听器
with app.app_context():
    enable_sqlite_foreign_keys(db.engine)


migrate = Migrate(app, db)

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(node_bp)
app.register_blueprint(node_bp_node)
app.register_blueprint(system_bp)
app.register_blueprint(route_bp)
app.register_blueprint(acl_bp)
app.register_blueprint(preauthkey_bp)
app.register_blueprint(log_bp)

#定义一个定时任务函数,每个一个小时记录一下流量使用情况
def my_task():
    with app.app_context():
        return get_data_record()
# 创建调度器
scheduler = BackgroundScheduler()
# 添加任务，每隔 10 秒执行一次
scheduler.add_job(func=my_task, trigger='interval',seconds=3600)
# 启动调度器
scheduler.start()


@app.route('/')
def index():
    return 'Flask 应用正在运行！'

# 自定义404错误处理器
@app.errorhandler(404)
def page_not_found(e):
    return render_template('auth/error.html',message="404")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)
