import math
from flask_login import login_required
from flask import Blueprint, json, current_app
from utils import get_sys_info, get_data_record


bp = Blueprint("system", __name__, url_prefix='/api/system')


# 获取系统相关信息
@bp.route('/info', methods=['GET'])
@login_required
def get_info():
    return get_sys_info()


# 获取数据
@bp.route('/data_usage', methods=['GET'])
@login_required
def data_usage():
    with open(current_app.config['NET_TRAFFIC_RECORD_FILE'], 'r') as file:
        content = file.read()
        json_data = json.loads(content)

        data_dict = json_data

        # 处理 recv 字典
        recv_values = list(data_dict['recv'].values())
        new_recv_values = [math.ceil(float(recv_values[i + 1]) - float(recv_values[i])) for i in
                           range(len(recv_values) - 1)]
        new_recv_dict = {f"{chr(ord('a') + i)}": str(new_recv_values[i]) for i in range(len(new_recv_values))}

        # 处理 sent 字典
        sent_values = list(data_dict['sent'].values())
        new_sent_values = [math.ceil(float(sent_values[i + 1]) - float(sent_values[i])) for i in
                           range(len(sent_values) - 1)]
        new_sent_dict = {f"{chr(ord('a') + i)}": str(new_sent_values[i]) for i in range(len(new_sent_values))}

        # 构建新的字典
        new_data_dict = {"recv": new_recv_dict, "sent": new_sent_dict}

        # 转换回 JSON 字符串并打印
        new_data = json.dumps(new_data_dict)

        return new_data


@bp.route('traffic_debug', methods=['GET'])
@login_required
def traffic_debug():
    return get_data_record()

@bp.route('visitor_distribution', methods=['GET'])
@login_required
def visitor_distribution():
    return current_app.config['REGION_DATA']
