from datetime import datetime, timedelta
import json
from utils import record_log, reload_headscale, to_rewrite_acl, to_request
from flask_login import login_user, logout_user, current_user, login_required
from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, json
from exts import SqliteDB
from utils import res
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

    with SqliteDB() as cursor:
        # 查询当前用户的节点数量
        query = "SELECT COUNT(*) as count FROM nodes WHERE user_id =?;"
        cursor.execute(query, (current_user.id,))
        result = cursor.fetchone()
        node_count = result['count'] if result else 0

        # 查询当前用户允许的节点数
        user_query = "SELECT node FROM users WHERE id =?;"
        cursor.execute(user_query, (current_user.id,))
        user_result = cursor.fetchone()
        user_node_limit = user_result['node'] if user_result else 0

    if int(node_count) >= int(user_node_limit):
        return res('2', '超过此用户节点限制', '')
    else:

        result_post = to_request('POST',url_path)
        if result_post['code'] == '0':
            record_log(current_user.id,"节点添加成功")
            return res('0', '节点添加成功', result_post['data'])
        else:
            return res(result_post['code'], result_post['msg'])

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
    if current_app.config['OPEN_USER_REG'] != 'on':
        return '<h1>当前服务器已关闭对外注册</h1>'
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


            if (username == "admin"):
                role = "manager"
                expire = create_time + timedelta(1000)
            else:
                role = "user"
                expire = create_time + timedelta(days=int(default_reg_days))  # 新用户注册默认?天后到期

            default_reg_days = 1 if default_reg_days != 0 else default_reg_days # 若用户注册默认天数不为0，代表该用户启用


            # headscale用户注册请求参数构建
            json_data =  {
              "name": username,
              "displayName": username,
              "email": email,
              "pictureUrl": "NULL"
            }

            result_reg = to_request('POST','/api/v1/user',data = json_data)  # 直接使用数据库创建用户会出现ACL失效，所有使用api创建

            if result_reg['code'] == '0':
                try:
                    user_id = json.loads(result_reg['data'])['user']['id']   # 获取 user_id
                except Exception as e:
                    print(f"发生错误: {e}")
                    return res('1','注册失败',result_reg['data'])
            else:
                return res('1', result_reg['msg'])


            with SqliteDB() as cursor:
                update_query = """
                        UPDATE users 
                        SET password = ?,created_at = ?,updated_at = ?,expire = ?,role = ?,cellphone = ?,node = ?,route = ?,enable = ?
                        WHERE name = ?
                    """
                values = (
                    password, create_time, create_time, expire, role, phone_number, current_app.config['DEFAULT_NODE_COUNT'], '0',
                    default_reg_days, username
                )
                cursor.execute(update_query, values)

                # 初始化用户ACL规则
                init_acl = f'{{"action": "accept","src": ["{username}@"],"dst": ["{username}@:*"]}}'
                insert_query = "INSERT INTO acl (acl, user_id) VALUES (?,?);"
                cursor.execute(insert_query, (init_acl, user_id))

            # 用户初始化
            to_rewrite_acl()
            reload_headscale()

            return res('0','注册成功','')

        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            return res('1', str(first_value[0]),'')


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

            record_log(user.id,"登录成功")
 
        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            res_code,res_msg,res_data ='1',str(first_value[0]),''
        return res(res_code,res_msg,res_data)
#
#
#

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
        new_password = form.new_password.data
        with SqliteDB() as cursor:
            hashed_password = generate_password_hash(new_password)
            # 更新用户密码
            update_query = "UPDATE users SET password =? WHERE id =?;"
            cursor.execute(update_query, (hashed_password, current_user.id))
            res_code, res_msg, res_data = '0', '修改成功', ''
            logout_user()
    else:
        first_key = next(iter(form.errors.keys()))
        first_value = form.errors[first_key]
        res_code, res_msg, res_data = '1', str(first_value[0]), ''

    return res(res_code, res_msg, res_data)



@bp.route('/error')
@login_required
def error():
    return render_template('auth/error.html')

