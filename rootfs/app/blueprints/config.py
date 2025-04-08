import json
from flask_login import login_required
from exts import db
from login_setup import role_required
from models import UserModel,  ConfigModel
from flask import Blueprint,  request


bp = Blueprint("config", __name__, url_prefix='/api/config')


res_json = {'code': '', 'data': '', 'msg': ''}


@bp.route('/getConfig',methods=['POST'])
@login_required
@role_required("manager")
def getConfig():
      query = ConfigModel.query.with_entities(
           ConfigModel.id,
           ConfigModel.acceptlogin,
           ConfigModel.acceptreg,
           ConfigModel.acceptnewlogin
      )
      config = query.first()
      if config:
           #对数据进行格式化
           config_data = {
                "id": config.id,
                "acceptlogin": config.acceptlogin,
                "acceptreg": config.acceptreg,
                "acceptnewlogin": config.acceptnewlogin
           }
           res_json['code'], res_json['msg'] = '0', '获取成功'
           res_json['data'] = config_data
      else:
              res_json['code'], res_json['msg'] = '1', '获取失败'
              res_json['data'] = {}

      return res_json

@bp.route('/updateConfig', methods=['POST'])
@login_required
@role_required("manager")
def updateConfig():
    # 获取请求数据
    acceptlogin = request.form.get('acceptlogin')
    acceptreg = request.form.get('acceptreg')
    acceptnewlogin= request.form.get('acceptnewlogin')

    # 更新数据库中的配置
    config = ConfigModel.query.first()
    if config:
        if acceptlogin:
           config.acceptlogin = acceptlogin
           if acceptlogin == '1':
                # 禁用登录则更新全部user表的数据
                users = UserModel.query.filter(UserModel.role != 'manager').all()
                for user in users:
                    user.enable = '0'
        if acceptreg:   
            config.acceptreg = acceptreg
        if acceptnewlogin:    
            config.acceptnewlogin = acceptnewlogin
        db.session.commit()
        res_json['code'], res_json['msg'] = '0', '更新成功'
    else:
        res_json['code'], res_json['msg'] = '1', '更新失败'

    return res_json