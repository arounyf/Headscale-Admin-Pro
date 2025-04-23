import json
import math
import os
from flask import current_app
import psutil
from exts import db
from datetime import datetime
import subprocess
import requests

from models import ACLModel, UserModel


# api接口返回格式定义
def res(code=None, msg=None, data=None):
    if code is None: code = '1'
    if msg is None: msg = "msg未初始化"
    if data is None: data = {}
    response = { "code": code,"msg": msg,"data": data}
    return response



def to_post(url_path,data=None):
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = server_host+url_path
    response = requests.post(url, headers=headers,data=data)
    print(f'post请求url地址: {url},返回消息: {response.text}')
    return response


def record_log(user_id, log_content):
    from models import LogModel
    """
    记录日志到数据库
    :param user_id: 用户 ID
    :param log_content: 日志内容
    :return: 成功返回 True，失败返回 False
    """
    try:
        # 创建日志记录实例
        new_log = LogModel(
            user_id=user_id,
            content=log_content,
            created_at=datetime.now()
        )
        # 将实例添加到数据库会话
        db.session.add(new_log)
        # 提交会话以保存更改
        db.session.commit()
        return True
    except Exception as e:
        # 若出现异常，回滚会话
        db.session.rollback()
        print(f"日志记录失败: {e}")
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
    res_json = {'code': '', 'data': '', 'msg': ''}
    # 定义日志文件路径
    log_file_path = os.path.join('/var/lib/headscale', 'headscale.log')
    # 以追加模式打开日志文件
    try:
        with open(log_file_path, 'a') as log_file:
            # 启动 headscale serve 进程，并将标准输出和标准错误输出重定向到日志文件
            subprocess.Popen(['headscale', 'serve'], stdout=log_file, stderr=log_file)
        res_json['code'], res_json['msg'], res_json['data'] = '0', '启动成功', ""
    except Exception as e:
        res_json = {'code': '1', 'msg': f'启动失败: {str(e)}', 'data': ''}
    return res_json


def stop_headscale():
    res_json = {'code': '', 'data': '', 'msg': ''}
    try:
        reload_command = "kill -9 $(ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1)"
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
            return int(pid)
        else:
            print("未找到 headscale serve 进程的 PID。")
            return False
    except subprocess.CalledProcessError as e:
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
    # acls = ACLModel.query.filter(ACLModel.enable == 1).all()

    acls = db.session.query(ACLModel).select_from(ACLModel).join(
        UserModel, ACLModel.user_id == UserModel.id).filter(
        UserModel.enable == '1').all(
    )

    acl_list = [json.loads(acl.acl) for acl in acls]
    acl_data = {
        "acls": acl_list
    }
    print(acl_data)
    try:
        with open(acl_path, 'w') as f:
            json.dump(acl_data, f, indent=4)
        code,msg,data = '0','写入成功',acl_data
    except Exception as e:
        # return f"写入文件时出错: {str(e)}", 500
        code,msg,data = '0','写入失败',str(e)

    return res(code,msg,data)