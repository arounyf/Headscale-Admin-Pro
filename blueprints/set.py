import subprocess

from flask_login import login_required

from exts import db
from login_setup import role_required
from flask import Blueprint, request,current_app
from ruamel.yaml import YAML

from models import ApiKeys

bp = Blueprint("set", __name__, url_prefix='/api/set')


res_json = {'code': '', 'data': '', 'msg': ''}


@bp.route('/upset' , methods=['GET','POST'])
@login_required
@role_required("manager")
def upset():
    apikey = request.form.get('apiKey')
    server_net = request.form.get('serverNet')
    server_url = request.form.get('serverUrl')
    region_html = request.form.get('regionHtml')


    # 创建 YAML 对象，设置保留注释
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    # 读取 YAML 配置文件
    with open('/etc/headscale/config.yaml', 'r') as file:
        config_yaml = yaml.load(file)

    # 修改配置项的值
    config_yaml['apikey'] = apikey
    config_yaml['server_url'] = server_url
    config_yaml['server_net'] = server_net
    config_yaml['region_html'] = region_html

    current_app.config['BEARER_TOKEN'] = config_yaml['apikey']
    current_app.config['SERVER_URL'] = config_yaml['server_url']
    current_app.config['SERVER_NET'] = config_yaml['server_net']
    current_app.config['REGION_HTML'] = config_yaml['region_html']


    # 将更新后的配置写回到文件
    with open('/etc/headscale/config.yaml', 'w') as file:
        yaml.dump(config_yaml, file)


    res_json['code'], res_json['msg'] = '0', '修改成功'
    res_json['data'] = ""


    return res_json



@bp.route('/get_apikey' , methods=['POST'])
@login_required
@role_required("manager")
def get_apikey():
    #获取之前先清理
    try:
        # 删除所有记录
        num_rows_deleted = ApiKeys.query.delete()
        # 提交事务
        db.session.commit()
        print(f"成功删除 {num_rows_deleted} 条记录")
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        print(f"删除记录时出现错误: {e}")

    try:
        # 执行 重载ACL 命令
        # result = subprocess.run(['systemctl', 'reload', 'headscale'], check=True, capture_output=True, text=True)
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)

        res_json['code'], res_json['msg'], res_json['data'] = '0', '执行成功', result.stdout
    except subprocess.CalledProcessError as e:
        res_json['code'], res_json['msg'], res_json['data'] = '1', '执行失败', f"错误信息：{e.stderr}"



    return res_json


