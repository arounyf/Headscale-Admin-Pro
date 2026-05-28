import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
import json
from utils import record_log, reload_headscale, to_rewrite_acl, to_request, reset_login_failures, send_email, generate_email_token, verify_email_token, get_ip_location, check_account_locked, record_login_failure
from flask_login import login_user, logout_user, current_user, login_required
from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, json
from exts import SqliteDB
from utils import res
from .forms import RegisterForm, LoginForm, PasswdForm
from werkzeug.security import generate_password_hash
from .get_captcha import get_captcha_code_and_content


# 登录频率限制：每个 IP 每分钟最多 10 次
_login_attempts = defaultdict(list)
_LOGIN_LIMIT = 10
_LOGIN_WINDOW = 60


def _check_login_rate(ip):
    now = time.time()
    cutoff = now - _LOGIN_WINDOW
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
    if len(_login_attempts[ip]) >= _LOGIN_LIMIT:
        return False
    _login_attempts[ip].append(now)
    return True




bp = Blueprint("auth", __name__, url_prefix='/')




@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/get_captcha')
def get_captcha():

    code,content = get_captcha_code_and_content()
    session['code'] = code
    return content


@bp.route('/send_email_code', methods=['POST'])
def send_email_code():
    email = request.form.get('email', '').strip()
    if not email:
        return res('1', '请输入邮箱', '')
    import random
    code = ''.join(random.choices('0123456789', k=4))
    session['email_code'] = code
    body = f'<h3>邮箱验证码</h3><p>你的验证码为：<b style="font-size:24px;color:#16baaa">{code}</b></p><p>5分钟内有效</p>'
    if send_email(email, '邮箱验证码', body):
        return res('0', '验证码已发送', '')
    return res('1', '验证码发送失败，请联系管理员', '')

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
            # 记录节点IP
            import threading
            app_ctx = current_app._get_current_object()
            def node_log():
                with app_ctx.app_context():
                    try:
                        node_data = json.loads(result_post['data'])
                        node_ip = node_data['node']['ipAddresses'][0]
                    except Exception:
                        node_ip = ''
                    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or request.remote_addr
                    ip_addr = ip_addr.split(",")[0].strip()
                    loc = get_ip_location(ip_addr)
                    msg = f"节点添加成功。节点IP：{node_ip}，请求IP：{ip_addr}"
                    if loc:
                        msg += f"，位置：{loc}"
                    record_log(current_user.id, msg)
            threading.Thread(target=node_log).start()
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
        if current_user.is_authenticated:
            return redirect(url_for('admin.admin'))
        else:
            email_verify = 'true' if current_app.config.get('EMAIL_VERIFY_REG', 'off') == 'on' else 'false'
            return render_template('auth/reg.html', email_verify=email_verify)
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

            email_verify = current_app.config.get('EMAIL_VERIFY_REG', 'off') == 'on'
            # 邮箱验证码模式下已在注册时验证了邮箱，直接启用；否则按天数判断
            enable_val = 0 if str(default_reg_days) == '0' else 1

            # headscale用户注册请求参数构建
            json_data =  {
              "name": username,
              "displayName": username,
              "email": email,
              "pictureUrl": "NULL"
            }

            result_reg = to_request('POST','/api/v1/user',data = json_data)

            if result_reg['code'] == '0':
                try:
                    user_id = json.loads(result_reg['data'])['user']['id']
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
                    enable_val, username
                )
                cursor.execute(update_query, values)

                # 获取本地用户ID用于ACL
                local_user = cursor.execute("SELECT id FROM users WHERE name = ?", (username,)).fetchone()
                local_user_id = local_user['id'] if local_user else user_id
                init_acl = f'{{"action": "accept","src": ["{username}@"],"dst": ["{username}@:*"]}}'
                cursor.execute("INSERT INTO acl (acl, user_id) VALUES (?,?);", (init_acl, local_user_id))

            to_rewrite_acl()
            reload_headscale()

            # 记录注册IP
            ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or request.remote_addr
            ip_addr = ip_addr.split(",")[0].strip()
            import threading
            app_ctx = current_app._get_current_object()
            def reg_log():
                with app_ctx.app_context():
                    with SqliteDB() as c:
                        u = c.execute("SELECT id FROM users WHERE name =?", (username,)).fetchone()
                        if u:
                            loc = get_ip_location(ip_addr)
                            record_log(u['id'], f"新用户注册。IP地址：{ip_addr}，位置：{loc}" if loc else f"新用户注册。IP地址：{ip_addr}")
            threading.Thread(target=reg_log).start()

            return res('0','注册成功','')

        else:
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            res_code, res_msg = '1', str(first_value[0])
            # 记录注册失败IP
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            username = request.form.get('username', '').strip()
            ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or request.remote_addr
            ip_addr = ip_addr.split(",")[0].strip()
            import threading
            app_ctx = current_app._get_current_object()
            def fail_reg_log():
                with app_ctx.app_context():
                    with SqliteDB() as c:
                        u = c.execute("SELECT id, name, email, cellphone FROM users WHERE email =? OR cellphone =?", (email, phone)).fetchone()
                    uid = u['id'] if u else None
                    loc = get_ip_location(ip_addr)
                    detail = ''
                    if u:
                        if u['email'] == email:
                            detail = f'，使用与用户 {u["name"]}(ID:{uid}) 相同的邮箱 {email}'
                        elif u['cellphone'] == phone:
                            detail = f'，使用与用户 {u["name"]}(ID:{uid}) 相同的手机号 {phone}'
                    msg = f"注册失败：{res_msg}，用户 {username} 注册失败{detail}。IP地址：{ip_addr}"
                    if loc: msg += f"，位置：{loc}"
                    record_log(uid, msg)
            threading.Thread(target=fail_reg_log).start()
            return res(res_code, res_msg, '')


@bp.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'GET':
        # 如果用户已经登录，重定向到 admin 页面
        if current_user.is_authenticated:
            return redirect(url_for('admin.admin'))
        else:
            return render_template('auth/login.html')
    else:
        if not _check_login_rate(request.remote_addr):
            return res('1', '登录过于频繁，请1分钟后再试', '')
        form = LoginForm(request.form)

        if form.validate():
            user = form.user  # 获取表单中查询到的用户对象
            login_user(user)
            reset_login_failures(user.name)
            res_code,res_msg,res_data = '0', '登录成功',''
            ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or request.remote_addr
            ip_addr = ip_addr.split(",")[0].strip()
            import threading
            app_ctx = current_app._get_current_object()
            def login_log():
                with app_ctx.app_context():
                    loc = get_ip_location(ip_addr)
                    msg = f"登录成功。IP地址：{ip_addr}"
                    if loc: msg += f"，位置：{loc}"
                    record_log(user.id, msg)
            threading.Thread(target=login_log).start()
 
        else:
            # return form.errors
            first_key = next(iter(form.errors.keys()))
            first_value = form.errors[first_key]
            res_code,res_msg,res_data ='1',str(first_value[0]),''
            # 记录登录失败IP
            username = request.form.get('username', '').strip()
            ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or request.remote_addr
            ip_addr = ip_addr.split(",")[0].strip()
            import threading
            app_ctx = current_app._get_current_object()
            def fail_log():
                with app_ctx.app_context():
                    with SqliteDB() as c:
                        u = c.execute("SELECT id FROM users WHERE name =?", (username,)).fetchone()
                    uid = u['id'] if u else None
                    loc = get_ip_location(ip_addr)
                    msg = f"登录失败：用户 {username}，{res_msg}。IP地址：{ip_addr}"
                    if loc: msg += f"，位置：{loc}"
                    record_log(uid, msg)
            threading.Thread(target=fail_log).start()
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


# ---- 邮箱验证 ----

@bp.route('/verify/<token>')
def verify_email(token):
    user_id = verify_email_token(token)
    if not user_id:
        return render_template('auth/error.html', message='验证链接已失效或已使用')
    with SqliteDB() as cursor:
        cursor.execute("UPDATE users SET enable = 1 WHERE id =?", (user_id,))
    return redirect(url_for('auth.login'))


# ---- 忘记密码 ----

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')
    code = session.pop('code', None)
    if not code or code != request.form.get('vercode', ''):
        return res('1', '验证码错误或已失效', '')
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    if not username:
        return res('1', '请输入用户名', '')
    if not email:
        return res('1', '请输入邮箱地址', '')
    if not phone:
        return res('1', '请输入手机号码', '')
    is_locked, remaining = check_account_locked(username)
    if is_locked:
        return res('1', f'账户已锁定，请{remaining}分钟后再试', '')
    with SqliteDB() as cursor:
        user = cursor.execute("SELECT id, name FROM users WHERE name =? AND email =? AND cellphone =?", (username, email, phone)).fetchone()
    if not user:
        record_login_failure(username)
        return res('1', '用户名、邮箱和手机号不匹配', '')
    reset_login_failures(username)
    import random, string
    new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    with SqliteDB() as cursor:
        cursor.execute("UPDATE users SET password =? WHERE id =?", (generate_password_hash(new_pass), user['id']))
    body = f'<h3>密码已重置</h3><p>用户 <b>{user["name"]}</b> 的新密码为：<b style="font-size:18px;color:#16baaa">{new_pass}</b></p><p>请登录后尽快修改密码。</p>'
    send_email(email, '密码重置', body)
    return res('0', '新密码已发送至邮箱，请查收', '')


@bp.route('/error')
@login_required
def error():
    return render_template('auth/error.html')

