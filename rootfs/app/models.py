from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Index

from exts import db

# ORM模型映射三部曲：
# 1、 python3 -m flask db init:只需要执行一次
# 2、python3 -m flask db migrate:识别ORM模型的改变，生成迁移脚本
# 3、python3 -m flask db upgrade:运行迁移脚本，同步到数据库中


class UserModel(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    name = db.Column(db.Text)
    display_name = db.Column(db.Text)
    email = db.Column(db.Text)
    provider_identifier = db.Column(db.Text)
    provider = db.Column(db.Text)
    profile_pic_url = db.Column(db.Text)

    password = db.Column(db.Text)
    expire = db.Column(db.DateTime)
    cellphone = db.Column(db.Text)
    role = db.Column(db.Text)
    enable = db.Column(db.Text)

    # 创建唯一索引
    Index('idx_name_no_provider_identifier', name, unique=True)
    Index('idx_name_provider_identifier', name, provider_identifier, unique=True)
    Index('idx_provider_identifier', provider_identifier, unique=True)
    Index('idx_users_deleted_at', deleted_at)


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


class Migrations(db.Model):
    __tablename__ = 'migrations'  # 表名

    # 列定义
    id = db.Column(db.Text, primary_key=True)  # 主键


class PreAuthKeysModel(db.Model):
    __tablename__ = 'pre_auth_keys'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.Text)
    user_id = db.Column(db.Integer)
    reusable = db.Column(db.Numeric)
    ephemeral = db.Column(db.Numeric, default=False)
    used = db.Column(db.Numeric, default=False)
    tags = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_pre_auth_keys_user',
            ondelete='SET NULL'
        ),
    )


class NodeModel(db.Model):
    __tablename__ = 'nodes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    machine_key = db.Column(db.Text)
    node_key = db.Column(db.Text)
    disco_key = db.Column(db.Text)
    endpoints = db.Column(db.Text)
    host_info = db.Column(db.Text)
    ipv4 = db.Column(db.Text)
    ipv6 = db.Column(db.Text)
    hostname = db.Column(db.Text)
    given_name = db.Column(db.String(63))
    user_id = db.Column(db.Integer)
    register_method = db.Column(db.Text)
    forced_tags = db.Column(db.Text)
    auth_key_id = db.Column(db.Integer)
    last_seen = db.Column(db.DateTime)
    expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_nodes_user',
            ondelete='CASCADE'
        ),
        db.ForeignKeyConstraint(
            ['auth_key_id'],
            ['pre_auth_keys.id'],
            name='fk_nodes_auth_key'
        ),
    )
    user = db.relationship('UserModel', backref=db.backref('NodeModel', cascade='all, delete-orphan'))
    auth_key = db.relationship('PreAuthKeysModel', backref=db.backref('NodeModel', lazy='dynamic'))


class Policies(db.Model):
    __tablename__ = 'policies'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    data = db.Column(db.Text)
    __table_args__ = (
        Index('idx_policies_deleted_at', 'deleted_at'),
    )


class RouteModel(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    node_id = db.Column(db.Integer, nullable=False)
    prefix = db.Column(db.Text)
    advertised = db.Column(db.Numeric)
    enabled = db.Column(db.Numeric)
    is_primary = db.Column(db.Numeric)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['node_id'],
            ['nodes.id'],
            name='fk_nodes_routes',
            ondelete='CASCADE'
        ),
        db.Index('idx_routes_deleted_at', 'deleted_at')
    )


class ACLModel(db.Model):
    __tablename__ = 'acl'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    acl = db.Column(db.Text)
    user_id = db.Column(db.Text)
    __table_args__ = (
        Index('idx_acl_user_id', 'user_id'),
    )


class LogModel(db.Model):
    __tablename__ = 'log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Text)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    __table_args__ = (
        Index('idx_log_user_id', 'user_id'),
    )