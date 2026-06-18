import json
import math
import os
import subprocess
import sys
import time
import requests
import psutil

from flask import current_app, session
from ruamel.yaml import YAML
from datetime import datetime, timezone, timedelta
from exts import SqliteDB


# api接口返回格式定义
def res(code=None, msg=None, data=None):
    if code is None: code = '1'
    if msg is None: msg = "msg未初始化"
    if data is None: data = {}
    response = { "code": code,"msg": msg,"data": data}
    return response


def table_res(code=None, msg=None, data=None, count=None, total_row_count = None):
    if code is None: code = '1'
    if msg is None: msg = "msg未初始化"
    if data is None: data = {}
    if count is None: count = 0
    if total_row_count is None: total_row_count = 0

    response = {
        'code': code,
        'msg': msg,
        'data': data,
        'count': count,
        'totalRow': {
            'count': total_row_count
        }
    }
    return response


def to_request(method,url_path,data=None,flag = True):
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = server_host+url_path

    request_method = getattr(requests, method.lower())
    response = request_method(url, headers=headers, json=data)

    if current_app.debug:
        print(f'{method} {url} -> {response.status_code}')


    # 如果返回Unauthorized则自动刷新apikey
    if response.text == "Unauthorized" and flag:
        refresh_result = to_refresh_apikey()
        if refresh_result['code'] == '0':
            current_app.config['BEARER_TOKEN'] = refresh_result['data']
            return to_request(method, url_path, data, False)
        else:
            return res('1', 'apikey刷新失败', '')
    else:
        return res('0','请求成功',response.text)







def record_log(user_id, log_content):
    try:
        with SqliteDB() as cursor:
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "INSERT INTO log (user_id, content, created_at) VALUES (?,?,?);",
                (user_id, log_content, current_time)
            )
            return True
    except Exception as e:
        print(f"记录日志失败: {e}")
        return False



# 获取流量、cpu、内存使用情况
def get_sys_info():
    cpu_usage = psutil.cpu_percent()

    memory_info = psutil.virtual_memory()
    memory_usage_percent = memory_info.percent

    recv = {}
    sent = {}
    

    net_interface = current_app.config['SERVER_NET']
    data = psutil.net_io_counters(pernic=True)
    interfaces = data.keys()
    
    sent_speed = recv_speed = 0

    for interface in interfaces:
        #print(interface)
        if interface == net_interface:  # 只处理 ens18 网卡
            sent.setdefault(interface, data.get(interface).bytes_sent)
            recv.setdefault(interface, data.get(interface).bytes_recv)

            sent_speed = math.ceil(sent.get(net_interface) / 1024)
            recv_speed = math.ceil(recv.get(net_interface) / 1024)

    info_dict = {
        'cpu_usage': cpu_usage,
        'memory_usage_percent': memory_usage_percent,
        'sent_speed': sent_speed,
        'recv_speed': recv_speed
    }

    return json.dumps(info_dict)




# 记录最新的25个流量记录
def get_data_record():
    json_data_now = json.loads(get_sys_info())

    recv_speed = str(json_data_now["recv_speed"])
    sent_speed = str(json_data_now["sent_speed"])

    with open(current_app.config['NET_TRAFFIC_RECORD_FILE'], 'r') as file:
        content = file.read()
        json_data_local = json.loads(content)

        keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y']
        for i in range(len(keys) - 1):
            json_data_local['sent'][keys[i]] = json_data_local['sent'][keys[i + 1]]
            json_data_local['recv'][keys[i]] = json_data_local['recv'][keys[i + 1]]

        json_data_local["sent"]["y"] = sent_speed
        json_data_local["recv"]["y"] = recv_speed

    with open(current_app.config['NET_TRAFFIC_RECORD_FILE'], 'w') as file:
        json.dump(json_data_local, file, indent=4)

    return json_data_local




def reload_headscale():
    res_json = {'code': '', 'data': '', 'msg': ''}
    # kill -HUP $(ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1)
    try:
        # 执行重载headscale命令
        # result = subprocess.run(['systemctl', 'reload', 'headscale'], check=True, capture_output=True, text=True)
        reload_command = "kill -HUP $(ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1)"
        result = subprocess.run(reload_command, shell=True, capture_output=True, text=True, check=True)
        
        res_json['code'], res_json['msg'] ,res_json['data']= '0', '执行成功',result.stdout
    except subprocess.CalledProcessError as e:
        res_json['code'], res_json['msg'], res_json['data'] = '1', '执行失败', f"错误信息：{e.stderr}"
    return res_json



def get_server_net():
    try:
        # 执行系统命令获取网卡信息
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, check=True)
        output = result.stdout

        # 解析输出结果，提取网卡名
        interfaces = []
        for line in output.split('\n'):
            if line.strip().startswith('1:') or line.strip().startswith('2:'):
                # 提取网卡名
                interface = line.split(':')[1].strip()
                interfaces.append(interface)

        return {'network_interfaces': interfaces}
    except subprocess.CalledProcessError as e:
        return {'error': f'执行命令时出错: {e.stderr}'}, 500
    except Exception as e:
        return {'error': f'发生未知错误: {str(e)}'}, 500



def start_headscale():
    log_file_path = os.path.join('/var/lib/headscale', 'headscale.log')

    if get_headscale_pid():
        return  res('0', '检测到headscale已启动')

    try:
        with open(log_file_path, 'a') as log_file:
            # 启动 headscale serve 进程，并将标准输出和标准错误输出重定向到日志文件
            subprocess.Popen(['headscale', 'serve'], stdout=log_file, stderr=log_file)
        return res('0', '启动成功')
    except Exception as e:
        return res('1', f'启动失败: {str(e)}')


def stop_headscale():
    res_json = {'code': '', 'data': '', 'msg': ''}
    try:
        reload_command = "kill -15 $(ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1)"
        result = subprocess.run(reload_command, shell=True, capture_output=True, text=True, check=True)
        res_json['code'], res_json['msg'], res_json['data'] = '0', '停止成功', result.stdout
    except subprocess.CalledProcessError as e:
        res_json['code'], res_json['msg'], res_json['data'] = '1', '执行失败', f"错误信息：{e.stderr}"
    return res_json



def get_headscale_pid():
    try:
        # 执行获取 headscale 进程 PID 的命令
        command = "ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        pid = result.stdout.strip()
        if pid:
            print(f"headscale pid is {pid}")
            return int(pid)
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(f"执行命令时出现错误: {e.stderr}")
        print(f"执行命令时出现错误: {e.stderr}")
        return False
    except ValueError:
        print("获取的 PID 无法转换为整数。")
        return False

def get_headscale_version():
    try:
        # 执行获取 headscale 进程 PID 的命令
        command = "headscale version"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print({e.stderr})

def to_rewrite_acl():
    """将所有 ACL 规则（全局 + 各用户启用）合并写入 headscale 策略文件"""
    acl_path = current_app.config['ACL_PATH']

    with SqliteDB() as cursor:
        # 全局规则（user_id = 0）+ 启用用户的规则
        query = """
            SELECT acl.acl
            FROM acl
            LEFT JOIN users ON acl.user_id = users.id
            WHERE acl.user_id = 0
               OR (acl.user_id > 0 AND users.enable = '1')
        """
        cursor.execute(query)
        acls = cursor.fetchall()

    acl_list = [json.loads(acl['acl']) for acl in acls]
    acl_data = {
        "randomizeClientPort": False,
        "acls": acl_list
    }

    try:
        with open(acl_path, 'w') as f:
            json.dump(acl_data, f, indent=4)
        return res('0', '写入成功', acl_data)
    except Exception as e:
        return res('1', '写入失败', str(e))



def save_config_yaml(config_dict):
    print(config_dict)
    # 创建 YAML 对象，设置保留注释
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    # 读取 YAML 配置文件

    with open('/etc/headscale/config.yaml', 'r') as file:
        config_yaml = yaml.load(file)

    for key, value in config_dict.items():
        current_app.config[key] = value
        config_yaml[key.lower()] = value

        # 将更新后的配置写回到文件
    with open('/etc/headscale/config.yaml', 'w') as file:
        yaml.dump(config_yaml, file)


    return res('0', '修改成功', '')





def to_refresh_apikey():
    try:
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)
        apikey = result.stdout.strip()
        config_mapping = {
            'BEARER_TOKEN': apikey
        }
        save_config_yaml(config_mapping)
        code, msg, data = '0','获取apikey成功',apikey
    except subprocess.CalledProcessError as e:
        code, msg, data = '1', '执行失败', f"错误信息：{e.stderr}"

    return res(code, msg, data)



def get_headscale_status(app):
    """
    检查 headscale 的健康状态。
    如果启动失败，抓取并显示本次启动尝试产生的所有日志。
    """
    with app.app_context():
        url = current_app.config['SERVER_HOST'] + '/health'
        log_file_path = '/var/lib/headscale/headscale.log'

    # 记录日志文件初始大小
    log_start_pos = 0
    if os.path.exists(log_file_path):
        try:
            log_start_pos = os.path.getsize(log_file_path)
        except OSError as e:
            print(f"Warning: Could not get size of log file: {e}")

    print(f"Health check started. Monitoring log file from position: {log_start_pos}")

    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200 and response.json() == {"status": "pass"}:
                print("Success: Headscale is healthy and running.")
                return True
            else:
                print(f"Attempt {attempt + 1} failed. Status code: {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"Attempt {attempt + 1}/{max_attempts}: Headscale not ready yet...")

        attempt += 1
        time.sleep(1)

    # 从初始位置读取新日志
    print("\n" + "="*60)
    print("Error: Headscale failed to start properly.")
    print("="*60)
    print("Fetching all logs since health check started:")
    print("-" * 60)

    startup_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(log_start_pos)
                startup_logs = f.readlines()
        except OSError as e:
            print(f"Error reading log file: {e}")
    else:
        print(f"Error: Log file not found at: {log_file_path}")

    if startup_logs:
        # 打印所有新日志，并设置为红色
        for line in startup_logs:
            # \033[91m 开启红色，\033[0m 恢复默认颜色
            print("\033[91m" + line.strip() + "\033[0m")
    else:
        print("Warning: No new logs were generated during the health check.")
        print("This could mean headscale didn't start at all or the log path is incorrect.")

    print("="*60)
    print("Suggestions:")
    print(f"1. Check the full log for more context: `tail -n 200 {log_file_path}`")
    print("2. Verify the database migrations and integrity.")
    print("="*60)

    sys.exit(1)


def to_init_db(app):
    get_headscale_status(app)
    _init_app_tables()


# ---- 应用自定义表初始化 ----

def _init_app_tables():
    pass


# ---- 邮件发送 ----

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer


def _get_token_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='email-token')


def generate_email_token(user_id):
    """生成签名令牌，1小时有效，不存数据库"""
    return _get_token_serializer().dumps(user_id)


def verify_email_token(token):
    """验证签名令牌，返回 user_id 或 None"""
    try:
        return _get_token_serializer().loads(token, max_age=3600)
    except Exception:
        return None


def send_email(to_email, subject, body):
    host = current_app.config.get('SMTP_HOST', '')
    port = int(current_app.config.get('SMTP_PORT', '465'))
    user = current_app.config.get('SMTP_USER', '')
    password = current_app.config.get('SMTP_PASSWORD', '')
    from_addr = current_app.config.get('SMTP_FROM', user)
    from_name = current_app.config.get('SMTP_FROM_NAME', '')
    use_ssl = str(current_app.config.get('SMTP_SSL', 'true')).lower() in ('true', '1', 'yes', 'on')

    if not host or not user or not password:
        print('SMTP not configured, skip sending email')
        return False

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        print(f'SMTP connecting: {host}:{port} SSL={use_ssl} user={user}')
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=10) as s:
                s.login(user, password)
                s.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as s:
                s.starttls()
                s.login(user, password)
                s.sendmail(from_addr, [to_email], msg.as_string())
        print(f'Email sent to {to_email}')
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f'SMTP 认证失败: {e}')
        return False
    except Exception as e:
        print(f'Send email failed: {type(e).__name__}: {e}')
        return False




# ---- IP 地理位置 ----

import requests as _requests

_IP_CACHE_FILE = '/var/lib/headscale/ip_locations.json'


def _load_ip_cache():
    if os.path.exists(_IP_CACHE_FILE):
        try:
            with open(_IP_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_ip_cache(data):
    try:
        with open(_IP_CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def _is_private_ip(ip):
    """判断是否为内网/私有IP"""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback
    except ValueError:
        return ip.lower() in ('localhost',)



def get_ip_location(ip):
    """查询IP地理位置，JSON文件缓存。根据IP_API_SOURCE配置选择API"""
    from flask import current_app as ca
    source = ca.config.get('IP_API_SOURCE', 'none')
    if source == 'none':
        return ''
    if _is_private_ip(ip):
        return '内网IP'

    cache = _load_ip_cache()
    if ip in cache:
        return cache[ip]

    loc = ''
    if source == 'tianapi':
        loc = _query_tianapi(ip)
    elif source == 'ipapi':
        loc = _query_ipapi(ip)
    if not loc:
        return ''

    cache[ip] = loc
    _save_ip_cache(cache)
    return loc


def _query_tianapi(ip):
    from flask import current_app as ca
    api_key = ca.config.get('TIANAPI_KEY', '')
    if not api_key:
        return ''
    try:
        resp = _requests.get('https://apis.tianapi.com/ipquery/index',
                             params={'key': api_key, 'ip': ip, 'full': 1}, timeout=5)
        data = resp.json()
        if data.get('code') == 200:
            r = data['result']
            return f"{r.get('country','')} {r.get('province','')} {r.get('city','')} {r.get('district','')} {r.get('isp','')}"
    except Exception as e:
        print(f'[_query_tianapi] error: {e}')
    return ''


def _query_ipapi(ip):
    try:
        resp = _requests.get(f'http://ip-api.com/json/{ip}?lang=zh-CN', timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                return f"{data.get('country','')} {data.get('regionName','')} {data.get('city','')}"
    except Exception:
        pass
    return ''


# ---- 登录 IP 记录已合并到 record_log ----


# 账户锁定：连续 5 次登录失败后锁定 30 分钟
_LOGIN_FAILURES_FILE = '/var/lib/headscale/login_failures.json'
_MAX_LOGIN_FAILURES = 5
_LOCKOUT_MINUTES = 30


def _load_login_failures():
    if os.path.exists(_LOGIN_FAILURES_FILE):
        try:
            with open(_LOGIN_FAILURES_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_login_failures(data):
    try:
        with open(_LOGIN_FAILURES_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def check_account_locked(username):
    """返回 (is_locked, remaining_minutes)"""
    data = _load_login_failures()
    entry = data.get(username)
    if not entry or not entry.get('locked_until'):
        return False, 0
    try:
        until = datetime.fromisoformat(entry['locked_until'])
        if datetime.now() < until:
            remaining = int((until - datetime.now()).total_seconds() / 60) + 1
            return True, remaining
    except (ValueError, TypeError):
        pass
    return False, 0


def record_login_failure(username):
    data = _load_login_failures()
    entry = data.get(username, {'failures': 0, 'locked_until': None})
    # 如果锁定已过期，重置计数器
    if entry.get('locked_until'):
        try:
            if datetime.now() >= datetime.fromisoformat(entry['locked_until']):
                entry = {'failures': 0, 'locked_until': None}
        except (ValueError, TypeError):
            entry = {'failures': 0, 'locked_until': None}
    entry['failures'] = entry.get('failures', 0) + 1
    if entry['failures'] >= _MAX_LOGIN_FAILURES:
        entry['locked_until'] = (datetime.now() + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
    data[username] = entry
    _save_login_failures(data)


def reset_login_failures(username):
    data = _load_login_failures()
    if username in data:
        del data[username]
        _save_login_failures(data)


# ---- 用户模式 ----

def is_user_mode():
    """管理员切换到用户视角，只看自己的数据"""
    from flask_login import current_user
    return session.get('user_mode') == 'user' and current_user.role == 'manager'
    