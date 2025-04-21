from datetime import datetime, timedelta
import requests

from utils import record_log, reload_headscale, res
from flask_login import login_user, logout_user, current_user, login_required
from exts import db
from models import UserModel, ACLModel
from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, json
from .forms import RegisterForm, LoginForm, PasswdForm
from werkzeug.security import generate_password_hash
from .get_captcha import get_captcha_code_and_content


bp = Blueprint("auth", __name__, url_prefix='/')




@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/get_captcha')
def get_captcha():

    code,content = get_captcha_code_and_content()
    session['code'] = code
    return content


def register_node(registrationID):
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = f'{server_host}/api/v1/node/register?user={current_user.name}&key={registrationID}'
    response = requests.post(url, headers=headers)


    if response.text == "Unauthorized":
        res_code,res_msg,res_data  = '1','认证失败',''
    else:
        res_code,res_msg,res_data  = '0','节点添加成功',str(response.text)
        record_log(current_user.id, "节点添加成功")

    return res(res_code,res_msg,res_data)



@bp.route('/register/<registrationID>', methods=['GET', 'POST'])
def register(registrationID):
    if request.method == 'GET':
        # 如果用户已经登录，重定向到 admin 页面
        if current_user.is_authenticated:
            # 已登录，直接添加节点
            node_info = register_node(registrationID)['data']
            print(node_info)

            try:
                # 获取 ipAddresses 的值
                ip_addresses = json.loads(node_info)["node"]["ipAddresses"][0]
            except Exception as e:
                print(f"发生错误: {e}")
                ip_addresses = 'error'
            return render_template('admin/node.html', node_info = ip_addresses)
        else:
            return render_template('auth/register.html',registrationID = registrationID)
    else:
        form = LoginForm(request.form)

        if form.validate():
            user = form.user  # 获取表单中查询到的用户对象
            login_user(user)
            res_code,res_msg,res_data = '0','登录成功',''
        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            res_code, res_msg,res_data = '1',str(first_value[0]),''
        return res(res_code,res_msg,res_data)


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
            email = form.email.data

            create_time = datetime.now()
            expire = create_time + timedelta(days=int(current_app.config['DEFAULT_REG_DAYS'])) # 新用户注册默认?天后到期

            if (username == "admin"):
                role = "manager"
                expire = create_time + timedelta(999)
            else:
                role = "user"
            user = UserModel(
                name=username,
                password = password,
                created_at=create_time,
                updated_at=create_time,
                expire=expire,
                cellphone=phone_number,
                email=email,
                role=role,
                enable=1
            )
            db.session.add(user)
            db.session.commit()

            #acl操作
            init_acl = f'{{"action": "accept","src": ["{username}"],"dst": ["{username}:*"]}}'

            new_acl = ACLModel(acl=init_acl, user_id=user.id)
            db.session.add(new_acl)
            db.session.commit()

            res_code,res_msg,res_data = '0','注册成功',reload_headscale()

        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]

            res_code,res_msg,res_data = '1', str(first_value[0]),''
        return res(res_code,res_msg,res_data)



@bp.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'GET':
        # 如果用户已经登录，重定向到 admin 页面
        if current_user.is_authenticated:
            return redirect(url_for('admin.admin'))
        else:
            return render_template('auth/login.html')
    else:
        form = LoginForm(request.form)

        if form.validate():
            user = form.user  # 获取表单中查询到的用户对象
            login_user(user)
            res_code,res_msg,res_data = '0', '登录成功',''

            print(session)
            print("登录成功")
            session.permanent = True
            record_log(user.id, "登录成功")
        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            res_code,res_msg,res_data ='1',str(first_value[0]),''
        return res(res_code,res_msg,res_data)




@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    # session.clear()
    logout_user()
    res_code,res_msg,res_data  = '0', 'logout success',''
    return res(res_code,res_msg,res_data)


@bp.route('/password', methods=['GET','POST'])
@login_required
def password():
    form = PasswdForm(request.form)
    if form.validate():
        # current_user.id
        new_password = form.new_password.data
        user = UserModel.query.filter_by(id=current_user.id).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()
        res_code,res_msg,res_data = '0', '修改成功',''
        logout_user()
    else:
        # return form.errors
        first_key = next(iter(form.errors.keys()))
        first_value = form.errors[first_key]
        res_code,res_msg,res_data = '1',str(first_value[0]),''

    return res(res_code,res_msg,res_data)


@bp.route('/error')
@login_required
def error():
    return render_template('auth/error.html')

