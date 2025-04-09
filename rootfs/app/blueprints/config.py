import json
from flask_login import login_required
from exts import db
from login_setup import role_required
from models import UserModel,  ConfigModel
from flask import Blueprint,  request
from .database import DatabaseManager,ResponseResult

bp = Blueprint("config", __name__, url_prefix='/api/config')




@bp.route('/getConfig',methods=['POST'])
@login_required
@role_required("manager")
def getConfig():
      return DatabaseManager.getSysConfig().dist()

@bp.route('/updateConfig', methods=['POST'])
@login_required
@role_required("manager")
def updateConfig():
    # 获取请求数据
    acceptlogin = request.form.get('acceptlogin')
    acceptreg = request.form.get('acceptreg')
    acceptnewlogin= request.form.get('acceptnewlogin')
    return DatabaseManager(db).updateConfig(acceptlogin=acceptlogin,acceptreg=acceptreg,acceptnewlogin=acceptnewlogin).dist() 