from flask_login import UserMixin


# 定义 User 类，继承自 UserMixin 以适配 Flask-Login
class User(UserMixin):
    def __init__(self, id, name,  created_at, updated_at, email, password, expire, cellphone, role, node, route, enable):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.email = email


        self.password = password
        self.expire = expire
        self.cellphone = cellphone
        self.role = role
        self.node = node
        self.route = route
        self.enable = enable


