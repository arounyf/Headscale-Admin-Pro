import json
from dataclasses import dataclass, asdict
from exts import db
from models import UserModel, ACLModel
from typing import Any, List, Dict,Union

@dataclass
class ResponseResult:
    code: str
    msg: str
    count: int
    data: Union[List[Dict[str, Any]], Dict[str, Any], str]
    totalRow: Dict[str, int]

    def to_dict(self):
        return asdict(self)
    
    def __json__(self):
        return self.to_dict() 


# 数据库操作层
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

        
 