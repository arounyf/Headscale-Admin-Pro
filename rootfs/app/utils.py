import json
import math
import os
from flask import current_app
import psutil
from exts import db
from datetime import datetime
import subprocess



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

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json'), 'r') as file:
        content = file.read()
        json_data_local = json.loads(content)

        keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y']
        for i in range(len(keys) - 1):
            json_data_local['sent'][keys[i]] = json_data_local['sent'][keys[i + 1]]
            json_data_local['recv'][keys[i]] = json_data_local['recv'][keys[i + 1]]

        json_data_local["sent"]["y"] = sent_speed
        json_data_local["recv"]["y"] = recv_speed

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json'), 'w') as file:
        json.dump(json_data_local, file, indent=4)

    return json_data_local




def reload_headscale():
    res_json = {'code': '', 'data': '', 'msg': ''}
    # kill -HUP $(ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1)
    try:
        # 执行 重载ACL 命令
        #result = subprocess.run(['systemctl', 'reload', 'headscale'], check=True, capture_output=True, text=True)
        reload_command = "ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1"
        result = subprocess.run(reload_command, shell=True, capture_output=True, text=True, check=True)
        
        res_json['code'], res_json['msg'] ,res_json['data']= '0', '执行成功',result.stdout
    except subprocess.CalledProcessError as e:
        res_json['code'], res_json['msg'], res_json['data'] = '1', '执行失败', f"错误信息：{e.stderr}"
    return res_json