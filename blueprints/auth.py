from datetime import datetime, timedelta
import json
from utils import record_log, reload_headscale, res, to_post, to_rewrite_acl
from flask_login import login_user, logout_user, current_user, login_required
from exts import db
from models import UserModel, ACLModel, NodeModel
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

    url_path = f'/api/v1/node/register?user={current_user.name}&key={registrationID}'

    node_count = db.session.query(NodeModel).filter(
        NodeModel.user_id == current_user.id
    ).count()


    if int(node_count) >= int(current_user.node):
        code, msg, data = '2', '超过此用户节点限制', ''
    else:
        response = to_post(url_path).text
        if (response == "Unauthorized"):
            code, msg, data = '1', '认证失败', response
        else:
            code,msg,data  = '0','节点添加成功',str(response)
            record_log(current_user.id, "节点添加成功")

    return res(code,msg,data)



@bp.route('/register/<registrationID>', methods=['GET', 'POST'])
def register(registrationID):
    if request.method == 'GET':
        # 如果用户已经登录，重定向到 admin 页面
        if current_user.is_authenticated:
            # 已登录，直接添加节点
            register_node_response = register_node(registrationID)
            error_info = ''
            print(register_node_response)
            if register_node_response['code'] == '0':
                try:
                    # 获取 ipAddresses 的值
                    ip_address = json.loads(register_node_response['data'])["node"]["ipAddresses"][0]
                except Exception as e:
                    print(f"发生错误: {e}")
                    ip_address = 'error'  # headscale 错误提示
                    error_info = json.loads(register_node_response['data']).get('message')
            else:
                ip_address = 'error' # hs-admin 错误提示
                error_info = register_node_response['msg']

            return render_template('admin/node.html', error_info = error_info, ip_address = ip_address)
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
    if current_app.config['OPEN_USER_REG'] == 'on':
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
                default_reg_days = current_app.config['DEFAULT_REG_DAYS']

                create_time = datetime.now()
                expire = create_time + timedelta(days=int(default_reg_days)) # 新用户注册默认?天后到期

                if (username == "admin"):
                    role = "manager"
                    expire = create_time + timedelta(1000)
                else:
                    role = "user"
                if default_reg_days != 0:
                    default_reg_days = 1

                json_data =  {
                  "name": username,
                  "displayName": username,
                  "email": email,
                  "pictureUrl": "NULL"
                }

                result_reg = to_post('/api/v1/user',data = json_data).text  # 直接使用数据库创建用户会出现ACL失效，所有使用api创建

                try:
                    # 获取 user_id
                    user_id = json.loads(result_reg)['user']['id']
                except Exception as e:
                    print(f"发生错误: {e}")
                    user_id = False

                # 修改数据库以解决sqlalchemy对9位微秒的兼容性问题，以及填充字段
                if user_id:
                    db.session.query(UserModel).filter(UserModel.name == username).update(
                        {
                        UserModel.password: password,
                        UserModel.created_at: create_time,
                        UserModel.updated_at: create_time,
                        UserModel.expire: expire,
                        UserModel.role: role,
                        UserModel.cellphone: phone_number,
                        UserModel.node: current_app.config['DEFAULT_NODE_COUNT'],
                        UserModel.route: '0',
                        UserModel.enable: default_reg_days
                        }
                    )

                    # 添加ACL
                    init_acl = f'{{"action": "accept","src": ["{username}"],"dst": ["{username}:*"]}}'
                    new_acl = ACLModel(acl=init_acl, user_id=user_id)
                    db.session.add(new_acl)
                    db.session.commit()

                    # 用户初始化
                    to_rewrite_acl()
                    reload_headscale()

                    res_code,res_msg,res_data = '0','注册成功',''
                else:
                    res_code, res_msg, res_data = '1',json.loads(result_reg)['message'], ''
            else:
                # return form.errors
                first_key = next(iter(form.errors.keys()))
                first_value = form.errors[first_key]

                res_code,res_msg,res_data = '1', str(first_value[0]),''
            return res(res_code,res_msg,res_data)
    else:
        return '<h1>当前服务器已关闭对外注册</h1>'


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

