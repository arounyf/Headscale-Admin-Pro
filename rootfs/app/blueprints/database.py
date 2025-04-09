import json
from dataclasses import dataclass, asdict
from exts import db
from models import UserModel, ACLModel,ConfigModel,LogModel,PreAuthKeysModel,NodeModel,RouteModel
from typing import Any, List, Dict,Union
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from types import SimpleNamespace

@dataclass
class ResponseResult:
    code: str
    msg: str
    count: int
    data: Union[List[Dict[str, Any]], Dict[str, Any], str]
    totalRow: Dict[str, int]

    def to_dict(self):
        return asdict(self)




# 数据库操作层 不要引入视图操作层的内容
# 该类负责与数据库进行交互，执行CRUD操作
class DatabaseManager:
    def __init__(self, db):
        self.db = db

    # acl分页查询
    def get_acl(self, page=1, per_page=10):
      # 使用分页查询并直接返回字典格式
      pagination = ACLModel.query.with_entities(
        ACLModel.id.label('id'),
        ACLModel.acl.label('acl'),
        UserModel.name.label('userName')
      ).join(UserModel, ACLModel.user_id == UserModel.id).paginate(
        page=page, per_page=per_page, error_out=False
     )
      data = [row._asdict() for row in pagination.items]
      return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=data,
            totalRow={"count": len(data)}  # 当前页的记录数
        )
    
    def re_acl(self,acl_id,new_acl):
        acl = ACLModel.query.filter_by(id=acl_id).first()
        acl.acl = new_acl
        db.session.commit()


    def getConfig(self):
        config = ConfigModel.query.first()
        if not config:
            return SimpleNamespace(**{key: "0" for key in ConfigModel.__table__.columns.keys()})
        return SimpleNamespace(**{
            key: (getattr(config, key) or "0")
            for key in ConfigModel.__table__.columns.keys()
        })
    
    def addModel(self,model):
        # 检查是否是 SQLAlchemy 模型实例
        if not isinstance(model, db.Model):
          raise TypeError("传入的对象不是一个有效的 SQLAlchemy 模型实例")

        self.db.session.add(model)
        self.db.session.commit()

    def register_user(self, user, acl):
        if not isinstance(user, db.Model):
          raise TypeError("传入的user对象不是一个有效的 SQLAlchemy 模型实例")
        if not isinstance(acl, db.Model):
          raise TypeError("传入的acl对象不是一个有效的 SQLAlchemy 模型实例")
        try:
            with self.db.session.begin():
                self.db.session.add(user)
                self.db.session.flush()
                self.db.session.add(acl)
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    #修改密码
    def password(self,new_password,current_user):
        user = UserModel.query.filter_by(id=current_user.id).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()


       # 获取系统配置
    def getSysConfig(self):
      # 使用分页查询并直接返回字典格式
      config = ConfigModel.query.with_entities(
           ConfigModel.id,
           ConfigModel.acceptlogin,
           ConfigModel.acceptreg,
           ConfigModel.acceptnewlogin
      ).first()
      if config:
        return ResponseResult(
              code="0",
              msg="获取成功",
              count=0,
              data=config._asdict(),
              totalRow={}
          )
      else:
        return ResponseResult(
              code="1",
              msg="获取失败",
              count=0,
              data={},
              totalRow={}
          ) 

    def updateConfig(self,acceptlogin,acceptreg,acceptnewlogin):
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
            return ResponseResult(
                code="0",
                msg="更新成功",
                count=0,
                data=[],
                totalRow={}
            )
        else:
            return ResponseResult(
                code="1",
                msg="更新失败",
                count=0,
                data=[],
                totalRow={}
            )

    def getUserByName(self,name):
        return UserModel.query.filter_by(name=name).first()
        
    # 分页获取日志列表
    def getLogPagination(current_user,page=1,per_page=10):
        query = LogModel.query.with_entities(
        LogModel.id,
        LogModel.content,
        UserModel.name,
        func.strftime('%Y-%m-%d %H:%M:%S', PreAuthKeysModel.created_at,'localtime').label('create_time'),
        # 可以添加其他需要的字段
    ) .join(UserModel, LogModel.user_id == UserModel.id) 
        # 判断用户角色
        if current_user.role != 'manager':
            # 如果不是 manager，只查询当前用户的节点信息
            query = query.filter(LogModel.user_id == current_user.id)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        log_list = [row._asdict() for row in pagination.items]
        return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=log_list,
            totalRow={"count": len(log_list)}  # 当前页的记录数
        )
    
    def getNodePagination(current_user,page=1,per_page=10):
        query = NodeModel.query.with_entities(
            NodeModel.id.label('id'),
            UserModel.name.label('userName'),
            NodeModel.given_name.label('name'),
            NodeModel.user_id,
            NodeModel.ipv4.lable('ip'),
            NodeModel.host_info,
            func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.last_seen,'localtime').label('lastTime'),
            func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.expiry,'localtime').label('expiry'),
            func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.created_at,'localtime').label('createTime'),
            func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.updated_at,'localtime').label('updated_at'),
            func.strftime('%Y-%m-%d %H:%M:%S', NodeModel.deleted_at,'localtime').label('deleted_at')
            # 可以添加其他需要的字段
        ).join(UserModel, NodeModel.user_id == UserModel.id)
            # 判断用户角色
        if current_user.role != 'manager':
            # 如果不是 manager，只查询当前用户的节点信息
            query = query.filter(NodeModel.user_id == current_user.id)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        nodes = pagination.items
          # 数据格式化
        nodes_list = [{
                'id': node.id,
                'userName': node.userName,
                'name': node.name,
                'ip': node.ip,
                'lastTime': node.lastTime,
                'createTime':node.createTime,
                'OS': json.loads(node.host_info).get("OS")+json.loads(node.host_info).get("OSVersion"),
                'Client':json.loads(node.host_info).get("IPNVersion")


            } for node in nodes]
        return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=nodes_list,
            totalRow={"count": len(nodes)}  # 当前页的记录数
        )
    
    def getNodeById(self,machine_id):
        return NodeModel.query.filter_by(id=machine_id).first()
    


    def getPreAuthKeyPagination(current_user,page=1,per_page=10):
        query = PreAuthKeysModel.query.with_entities(
            PreAuthKeysModel.id,
            PreAuthKeysModel.key,
            UserModel.name,
            func.strftime('%Y-%m-%d %H:%M:%S', PreAuthKeysModel.created_at,'localtime').label('create_time'),
            func.strftime('%Y-%m-%d %H:%M:%S', PreAuthKeysModel.expiration,'localtime').label('expiration'),
            # 可以添加其他需要的字段
        ) .join(UserModel, PreAuthKeysModel.user_id == UserModel.id)
        # 判断用户角色
        if current_user.role != 'manager':
            # 如果不是 manager，只查询当前用户的节点信息
            query = query.filter(PreAuthKeysModel.user_id == current_user.id)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        PreAuthKeys_list = [row._asdict() for row in pagination.items]
          # 数据格式化
        return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=PreAuthKeys_list,
            totalRow={"count": len(pagination.items)}  # 当前页的记录数
        )
    
    def getRoutePagination(current_user,page=1,per_page=10):
        query = RouteModel.query.with_entities(
            RouteModel.id,
            UserModel.name,
            NodeModel.given_name.lablel('NodeName'),
            RouteModel.prefix.label('route'),
            RouteModel.enabled.label('enable'),
            func.strftime('%Y-%m-%d %H:%M:%S', RouteModel.created_at,'localtime').label('createTime')
            # 可以添加其他需要的字段
        ).join(
            NodeModel, RouteModel.node_id == NodeModel.id  # 假设 RouteModel 通过 node_id 关联 NodeModel
        ).join(
            UserModel, NodeModel.user_id == UserModel.id
        )
        # 判断用户角色
        if current_user.role != 'manager':
            # 如果不是 manager，只查询当前用户的节点信息
            query = query.filter(NodeModel.user_id == current_user.id)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        routes = pagination.items
          # 数据格式化
        routes_list = [row._asdict() for row in pagination.items]
        return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=routes_list,
            totalRow={"count": len(routes)}  # 当前页的记录数
        )
    

    def getUserPagination(page=1, per_page=10):
        # 使用 func.strftime 格式化时间字段
        query = UserModel.query.with_entities(
            UserModel.id,
            UserModel.name.label('userName'),
            func.strftime('%Y-%m-%d %H:%M:%S', UserModel.created_at, ).label('createTime'),
            UserModel.cellphone,
            func.strftime('%Y-%m-%d %H:%M:%S', UserModel.expire, ).label('expire'),
            UserModel.enable,
            UserModel.role
        )
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
        users_list = [row._asdict() for row in pagination.items]
        return ResponseResult(
            code="0",
            msg="获取成功",
            count=pagination.total,  # 总记录数
            data=users_list,
            totalRow={"count": len(users)}  # 当前页的记录数
        )
    
    def updateUserExpire(self,user_id,new_expire):
        user=UserModel.query.filter_by(id=user_id).first()
        user.expire = new_expire
        db.session.commit()
        return ResponseResult(
            code="0",
            msg="更新成功",
            count=0,
            data=[],
            totalRow={}
        )
    
    def userEnable(self,user_id,enable):
        user = UserModel.query.filter_by(id=user_id).first()
        if (user.role == 'manager'):
            code = '1'
            msg = ('管理员用户不可操作自己')
        if (enable == "true"):
            code='0'
            user.enable = 1
            msg = ('启用成功')
        else:
            code='0'
            user.enable = 0
            msg = ('关闭成功')
        db.session.commit()
        return ResponseResult(
            code=code,
            msg=msg,
            count=0,
            data=[],
            totalRow={}
        )
    
    def delUser(self,user_id):
        user = UserModel.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        return ResponseResult(
            code="0",
            msg="删除成功",
            count=0,
            data=[],
            totalRow={}
        )