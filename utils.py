import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import requests
import psutil

from flask import current_app
from ruamel.yaml import YAML
from datetime import datetime
from sqlalchemy.sql.functions import current_user
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


def to_post(url_path,data=None):
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = server_host+url_path
    response = requests.post(url, headers=headers,json=data)

    print(f'post请求url地址: {url},返回消息: {response.text}---------------------------------------')



    # 如果返回Unauthorized则自动刷新apikey
    if response.text == "Unauthorized":
        apikey = to_refresh_apikey()['data']
        print(f'------------apikey--------------{apikey}---------------------------------')
        headers = {
            'Authorization': f'Bearer {apikey}'
        }
        response = requests.post(url, headers=headers, json=data)

        print(f'post二次请求url地址: {url},返回消息: {response.text}---------------------------------------')

    return response


def record_log(log_content,user_id = None):
    """
    记录日志到数据库
    :param user_id: 用户 ID
    :param log_content: 日志内容
    :return: 成功返回 True，失败返回 False
    """

    if user_id == None:
        user_id = current_user.id
    with SqliteDB() as cursor:
        # 获取当前时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 插入日志记录的 SQL 语句
        insert_query = "INSERT INTO log (user_id, content, created_at) VALUES (?,?,?);"
        cursor.execute(insert_query, (user_id, log_content, current_time))
        return True





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
    print(acl_data)

    try:
        with open(acl_path, 'w') as f:
            json.dump(acl_data, f, indent=4)
        code, msg, data = '0', '写入成功', acl_data
    except Exception as e:
        code, msg, data = '1', '写入失败', str(e)

    return res(code, msg, data)

def save_config_yaml(config_dict):
    # 创建 YAML 对象，设置保留注释
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    # 读取 YAML 配置文件

    with open('/etc/headscale/config.yaml', 'r') as file:
        config_yaml = yaml.load(file)

    for key, value in config_dict.items():
        print(f"------------保存新的配置------------------Key: {key}, Value: {value}--------------------------")
        current_app.config[key] = value
        config_yaml[key.lower()] = value

        # 将更新后的配置写回到文件
    with open('/etc/headscale/config.yaml', 'w') as file:
        yaml.dump(config_yaml, file)

    code, msg, data = '0', '修改成功', ''
    return res(code, msg, data)





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
    with app.app_context():
        url = current_app.config['SERVER_HOST'] + '/health'
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(url)
            if response.json() == {"status": "pass"}:
                print("The headscale health status is pass!")
                return True
            else:
                print(f"The headscale health status is error!")
        except (requests.RequestException, ValueError):
            print("The status of headscale is being retrieved. Please wait.")
        attempt += 1
        time.sleep(1)
    print("Failed to get a valid headscale status after multiple attempts.")
    return False



def to_init_db(app):
    if not get_headscale_status(app):
        with open('/var/lib/headscale/headscale.log', 'r') as file:
            lines = file.readlines()
            last_five_lines = lines[-5:]
            print("------------------------headscale failed to boot. Here are some boot logs-----------------------------")
            for line in last_five_lines:
                print(line.strip())
        sys.exit(1)

    # 要添加的字段列表
    fields = [
        ('password', 'TEXT'),
        ('expire', 'DATETIME'),
        ('cellphone', 'TEXT'),
        ('role', 'TEXT'),
        ('enable', 'TEXT'),
        ('route', 'TEXT'),
        ('node', 'TEXT')
    ]

    with SqliteDB() as cursor:
        # 获取 users 表的所有列名
        cursor.execute("PRAGMA table_info(users);")
        existing_columns = [row[1] for row in cursor.fetchall()]

        for field, field_type in fields:
            if field not in existing_columns:
                # 若字段不存在，则添加该字段
                alter_query = f"ALTER TABLE users ADD COLUMN {field} {field_type};"
                try:
                    cursor.execute(alter_query)
                    print(f"add {field} to users db table")
                except Exception as e:
                    print(f"add {field} error: {e}")



    with SqliteDB() as cursor:

        # 检查 acl 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='acl';")
        acl_table_exists = cursor.fetchone()

        if not acl_table_exists:
            # 若 acl 表不存在，则创建该表
            create_table_query = """
            CREATE TABLE acl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acl TEXT,
                user_id INTEGER,
                CONSTRAINT `fk_acl_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            );
            """
            cursor.execute(create_table_query)

            # 创建索引
            create_index_query = "CREATE INDEX idx_acl_user_id ON acl (user_id);"
            cursor.execute(create_index_query)

            print("create acl db table is success")



        # 检查 log 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='log';")
        log_table_exists = cursor.fetchone()

        if not log_table_exists:
            # 若 log 表不存在，则创建该表
            create_table_query = """
            CREATE TABLE log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                created_at DATETIME,
                CONSTRAINT `fk_log_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            );
            """
            cursor.execute(create_table_query)

            # 创建索引
            create_index_query = "CREATE INDEX idx_log_user_id ON log (user_id);"
            cursor.execute(create_index_query)

            print("create log db table is success")
