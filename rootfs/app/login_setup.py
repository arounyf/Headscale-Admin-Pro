# login_setup.py
import functools

from flask import redirect, url_for, render_template
from flask_login import LoginManager, current_user
from models import UserModel


login_manager = LoginManager()


def init_login_manager(app):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.error'


# 自定义未授权处理函数
@login_manager.unauthorized_handler
def unauthorized():
    # 这里可以添加要传递的参数
    message = "未登录系统或需重新登录"
    return render_template('auth/error.html',message=message)


@login_manager.user_loader
def user_loader(username):
    try:
        # 根据用户名查询数据库中的用户
        user = UserModel.query.filter_by(id=username).first()
        if user:
            return user
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None


def role_required(role):
    def wrapper(fn):
        @functools.wraps(fn)  # 使用 functools.wraps 保留原函数元数据
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role != role:
                return 'You do not have permission to access this page.', 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper