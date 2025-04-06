import json
import math
import os
from flask import current_app
import psutil
from exts import db
from datetime import datetime
import subprocess
from flask import current_app
import requests 


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

     # 使用相对路径获取 data.json 文件
    data_file_path = os.path.join(os.path.dirname(__file__), 'data.json')

    with open(data_file_path, 'r') as file:
        content = file.read()
        json_data_local = json.loads(content)

        keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y']
        for i in range(len(keys) - 1):
            json_data_local['sent'][keys[i]] = json_data_local['sent'][keys[i + 1]]
            json_data_local['recv'][keys[i]] = json_data_local['recv'][keys[i + 1]]

        json_data_local["sent"]["y"] = sent_speed
        json_data_local["recv"]["y"] = recv_speed

    with open(data_file_path, 'w') as file:
        json.dump(json_data_local, file, indent=4)

    return json_data_local




def reload_headscale():
    res_json = {'code': '', 'data': '', 'msg': ''}
    acl_data=fecth_headscale()
    acl_data=acl_data.get('acls',{})
    result=set_headscale(acl_data)
    if result:
       res_json['code'], res_json['msg'] ,res_json['data']= '0', '执行成功',acl_data
    else:
       res_json['code'], res_json['msg'] ,res_json['data']= '1', '执行失败',acl_data
    return res_json
    

#设置acl规则
def set_headscale(acl): 
        server_host = current_app.config['SERVER_HOST']
        bearer_token = current_app.config['BEARER_TOKEN']
        headers = {
        'Authorization': f'Bearer {bearer_token}'
        }
        url = f'{server_host}/api/v1/policy'
        try:
            response = requests.put(url, data=acl,headers=headers)
            response_data = response.json()
            return response_data.get('data', {}).get('isSuccess')
        except Exception as e:
            return False
#获取acl规则
def fecth_headscale(): 
        server_host = current_app.config['SERVER_HOST']
        bearer_token = current_app.config['BEARER_TOKEN']
        headers = {
        'Authorization': f'Bearer {bearer_token}'
        }
        url = f'{server_host}/api/v1/policy'
        try:
            response = requests.get(url, headers=headers)
            response_data = json.loads(response.text)
            policy = json.loads(response_data.get('policy', '{}'))
            return policy
        except Exception as e:
            return None          