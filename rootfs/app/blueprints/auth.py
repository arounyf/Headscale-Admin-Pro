from datetime import datetime, timedelta
from utils import record_log, reload_headscale,set_headscale,fecth_headscale
from flask_login import login_user, logout_user, current_user, login_required
from exts import db
from models import UserModel, ACLModel,ConfigModel
from flask import Blueprint, render_template, request, session,  redirect, url_for
from .forms import RegisterForm, LoginForm, PasswdForm
from werkzeug.security import generate_password_hash
from .get_captcha import get_captcha_code_and_content
from sqlalchemy import  text
from .database import DatabaseManager,ResponseResult
bp = Blueprint("auth", __name__, url_prefix='/')


@bp.route('/')
def index():
    # 查询配置表是否允许新用户注册
    config = DatabaseManager(db).getConfig()
    # 默认不允许新用户注册
    return render_template('index.html',acceptreg=config.acceptreg)


@bp.route('/get_captcha')
def get_captcha():

    code,content = get_captcha_code_and_content()
    session['code'] = code
    return content


res_json = {'code': '', 'data': '', 'msg': ''}

@bp.route('/reg', methods=['GET','POST'])
def reg():
    if request.method == 'GET':
        # 如果用户已经登录，重定向到 admin 页面
        if current_user.is_authenticated:
            return redirect(url_for('admin.admin'))
        else:
            return render_template('auth/reg.html')
    else:

        form = RegisterForm(request.form)
        if form.validate():
            username = form.username.data
            password = generate_password_hash(form.password.data)
            phone_number = form.phone.data
            # 新注册用户从配置中取值,管理员启用才能登录
            config = DatabaseManager(db).getConfig()
            enable = config.acceptnewlogin
            create_time = datetime.now()
             
            if (username == "admin"):
                role = "manager"
                # 管理员注册默认100年到期
                expire = create_time + timedelta(days=36500)
            else:
                role = "user"
                # 新用户注册默认15天后到期
                expire = create_time + timedelta(days=15)
            try:    
                user = UserModel(name=username,password = password,created_at=create_time,updated_at=create_time,expire=expire,cellphone=phone_number,role=role,enable=enable)
                newAcl = f'{{"action": "accept","src": ["{username}"],"dst": ["{username}:*"]}}'
                new_acl = ACLModel(acl=newAcl, user_id=user.id)
                DatabaseManager(db).register_user(user,new_acl)
            except Exception as e:
                return ResponseResult(
                            code="1",
                            msg="注册失败,请稍后再试！",
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()
            return ResponseResult(
                            code="0",
                            msg="注册成功",
                            count=0,
                            data=reload_headscale(),
                            totalRow={}
                        ).to_dict()


        else:
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            return ResponseResult(
                            code="1",
                            msg=str(first_value[0]),
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()





@bp.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('admin.admin'))
        else:
            next_page = request.args.get('next', '')
            # 查询配置表是否允许新用户注册
            config = DatabaseManager(db).getConfig()
            # 默认不允许新用户注册
            return render_template('auth/login.html',next=next_page,acceptreg=config.acceptreg)
    else:
        form = LoginForm(request.form)

        if form.validate():
            user = form.user  # 获取表单中查询到的用户对象
            login_user(user)
            session.permanent = True
            record_log(user.id, "登录成功")

            # 登录成功后，获取 next 参数并跳转
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return ResponseResult(
                            code="0",
                            msg="登录成功",
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()
        else:
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            return ResponseResult(
                            code="1",
                            msg=str(first_value[0]),
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()



@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return ResponseResult(
                            code="0",
                            msg='注销成功',
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()


@bp.route('/password', methods=['GET','POST'])
@login_required
def password():
    form = PasswdForm(request.form)
    if form.validate():
        new_password = form.new_password.data
        DatabaseManager(db).password(new_password,current_user)
        logout_user()
        return ResponseResult(
                            code="0",
                            msg='修改成功',
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()
    else:
        first_key = next(iter(form.errors.keys()))
        first_value = form.errors[first_key]
        return ResponseResult(
                            code="0",
                            msg=str(first_value[0]),
                            count=0,
                            data=[],
                            totalRow={}
                        ).to_dict()



@bp.route('/error')
@login_required
def error():
    return render_template('auth/error.html')

