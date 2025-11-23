import json
import math
import os
import subprocess
import sys
import time
import requests
import psutil

from flask import current_app
from ruamel.yaml import YAML
from datetime import datetime,timezone
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

    # 动态调用 requests 库中的方法
    request_method = getattr(requests, method.lower())
    response = request_method(url, headers=headers, json=data)

    print(f'{method}请求url地址: {url},返回消息: {response.text}---------------------------------------')


    # 如果返回Unauthorized则自动刷新apikey
    if response.text == "Unauthorized" and flag:
        current_app.config['BEARER_TOKEN'] = to_refresh_apikey()['data']
        data = to_request('POST',url_path,data,False)['data']
        return res('0', '请求成功', data)
    else:
        return res('0','请求成功',response.text)







def record_log(user_id, log_content):
    """
    记录日志到数据库（使用 UTC 时间）
    :param user_id: 用户 ID
    :param log_content: 日志内容
    :return: 成功返回 True，失败返回 False
    """
    try:
        with SqliteDB() as cursor:
            # 获取当前 UTC 时间
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            insert_query = "INSERT INTO log (user_id, content, created_at) VALUES (?,?,?);"
            cursor.execute(insert_query, (user_id, log_content, current_time))
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
    # 定义日志文件路径
    log_file_path = os.path.join('/var/lib/headscale', 'headscale.log')

    # 以追加模式打开日志文件
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
    acl_path = current_app.config['ACL_PATH']

    with SqliteDB() as cursor:
        # 构建 SQL 查询语句
        query = """
            SELECT acl.acl
            FROM acl
            JOIN users user ON acl.user_id = user.id
            WHERE user.enable = '1'
        """
        cursor.execute(query)
        acls = cursor.fetchall()

    acl_list = [json.loads(acl['acl']) for acl in acls]
    acl_data = {
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

    max_attempts = 5
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
    #数据库修改已经集成到了headscale中
    