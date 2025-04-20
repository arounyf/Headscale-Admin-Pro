# ORM模型映射三部曲：
# 1、 python3 -m flask db init:只需要执行一次
# 2、python3 -m flask db migrate:识别ORM模型的改变，生成迁移脚本
# 3、python3 -m flask db upgrade:运行迁移脚本，同步到数据库中

from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Index, ForeignKeyConstraint,UniqueConstraint  # 新增 ForeignKeyConstraint 导入
from exts import db

class UserModel(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 添加默认值
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 添加默认值和更新触发
    deleted_at = db.Column(db.DateTime)
    name = db.Column(db.Text)
    display_name = db.Column(db.Text)
    email = db.Column(db.Text)  # 建议邮箱添加唯一约束
    provider_identifier = db.Column(db.Text)
    provider = db.Column(db.Text)
    profile_pic_url = db.Column(db.Text)
    password = db.Column(db.Text)

    # 项目新增字段
    expire = db.Column(db.DateTime)
    cellphone = db.Column(db.Text)
    role = db.Column(db.Text)
    enable = db.Column(db.Text)
    route = db.Column(db.Text)
    node = db.Column(db.Text)

    # 显式命名唯一索引（SQLite 不支持部分索引，此处直接创建普通唯一索引）
    __table_args__ = (
        UniqueConstraint('name', name='uq_users_name'),

        Index('idx_name_no_provider_identifier', 'name', sqlite_where=provider_identifier.is_(None)),  # 模拟部分索引（需 SQLite 支持）
        Index('idx_name_provider_identifier', 'name', 'provider_identifier'),
        Index('idx_provider_identifier', 'provider_identifier'),
        Index('idx_users_deleted_at', 'deleted_at'),
    )



class ApiKeys(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prefix = db.Column(db.Text)
    hash = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)

    __table_args__ = (
        Index('idx_api_keys_prefix', 'prefix', unique=True),
    )



class PreAuthKeysModel(db.Model):
    __tablename__ = 'pre_auth_keys'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.Text)  # 建议密钥添加唯一约束
    user_id = db.Column(db.Integer)  # 简化外键定义（配合 __table_args__）
    reusable = db.Column(db.NUMERIC)
    ephemeral = db.Column(db.NUMERIC, default=False)
    used = db.Column(db.NUMERIC, default=False)
    tags = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)

    # 显式命名外键约束（与 db.ForeignKey 配合）
    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name='fk_pre_auth_keys_user',
            ondelete='CASCADE'  # 外键删除策略
        ),
    )


class NodeModel(db.Model):
    __tablename__ = 'nodes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    machine_key = db.Column(db.Text)  # 建议机器密钥添加唯一约束
    node_key = db.Column(db.Text)
    disco_key = db.Column(db.Text)
    endpoints = db.Column(db.Text)
    host_info = db.Column(db.Text)
    ipv4 = db.Column(db.Text)
    ipv6 = db.Column(db.Text)
    hostname = db.Column(db.Text)
    given_name = db.Column(db.Text)
    user_id = db.Column(db.Integer)  # 简化外键定义
    register_method = db.Column(db.Text)
    forced_tags = db.Column(db.Text)
    auth_key_id = db.Column(db.Integer)  # 简化外键定义
    last_seen = db.Column(db.DateTime)
    expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)

    # 显式命名外键约束（与 db.ForeignKey 配合）
    __table_args__ = (

        ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name='fk_nodes_user',
            ondelete='CASCADE'
        ),
        ForeignKeyConstraint(
            ['auth_key_id'], ['pre_auth_keys.id'],
            name='fk_nodes_auth_key',
            ondelete='CASCADE'  # 建议改为 SET NULL（避免级联删除时意外删除 PreAuthKey）
        ),
    )



class Policies(db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    data = db.Column(db.Text)
    # 创建索引 idx_policies_deleted_at
    __table_args__ = (
        Index('idx_policies_deleted_at', 'deleted_at'),
    )


class RouteModel(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    node_id = db.Column(db.Integer,nullable=False)
    prefix = db.Column(db.Text)
    advertised = db.Column(db.Boolean)  # 改用 Boolean 类型
    enabled = db.Column(db.Boolean)
    is_primary = db.Column(db.Boolean)

    # 显式命名外键约束（与 db.ForeignKey 配合）
    __table_args__ = (
        ForeignKeyConstraint(
            ['node_id'], ['nodes.id'],
            name='fk_routes_node',
            ondelete='CASCADE'
        ),
        Index('idx_routes_deleted_at', 'deleted_at'),
    )


# 项目新增表
class ACLModel(db.Model):
    __tablename__ = 'acl'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    acl = db.Column(db.Text)
    user_id = db.Column(db.Integer)  # 添加正确外键（原代码为 Text 类型，应为 Integer）

    __table_args__ = (
        Index('idx_acl_user_id', 'user_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_acl_user'),  # 显式命名外键
    )

class LogModel(db.Model):
    __tablename__ = 'log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)  # 添加正确外键（原代码为 Text 类型，应为 Integer）
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    __table_args__ = (
        Index('idx_log_user_id', 'user_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_log_user'),  # 显式命名外键
    )