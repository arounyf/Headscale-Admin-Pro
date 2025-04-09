import wtforms
from flask import session
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms.validators import  length, DataRequired, Regexp, Length, EqualTo
from sqlalchemy import  text
from exts import db
from ..database import DatabaseManager

class RegisterForm(wtforms.Form):
    username = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='用户名格式错误')])
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    confirmPassword = wtforms.StringField(validators=[EqualTo('password',message='密码输入不一致')])
    phone = wtforms.StringField(validators=[DataRequired(),length(11, 11),Regexp(r'(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}', 0, '手机号码不合法')])
    vercode = wtforms.StringField(validators=[Length(min=4, max=4, message='验证码格式错误')])
    captcha_uuid = wtforms.StringField(validators=[Length(min=36, max=36, message='UUID错误')])




    def validate_vercode(self,field):
        code = session['code']
        if code != field.data:
            raise wtforms.ValidationError("验证码错误！")



    def validate_username(self,field):
         # 检查是否允许注册
        config = DatabaseManager(db).getConfig()
        # 数据库未配置则默认不允许注册
        if config:
            acceptreg = config.acceptnewlogin
        else:
            acceptreg = '0'
        if acceptreg == '0':    
            raise wtforms.ValidationError("当前系统禁止注册新用户！")    
        user = DatabaseManager(db).getUserByName(name=field.data)
        if user:
            raise wtforms.ValidationError("该用户已注册！")


class LoginForm(wtforms.Form):
    username = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='用户名格式错误')])
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    vercode = wtforms.StringField(validators=[Length(min=4, max=4, message='验证码格式错误')])
    captcha_uuid = wtforms.StringField(validators=[Length(min=36, max=36, message='UUID错误')])



    #user = None  # 用于存储查询到的用户对象

    def validate_vercode(self, field):
        code = session['code']
        if code != field.data:
            raise wtforms.ValidationError("验证码错误！")

    def validate_username(self, field):

        # python不支持超过6位数的微秒,但是headscale的微秒都是9位，所以出此下策
        # 目前发现使用headscale user create创建的时间存在9位微秒

        try:
            user = DatabaseManager(db).getUserByName(name=field.data)
        except Exception as e:
            if (type(e).__name__ == "ValueError"):
                raise wtforms.ValidationError("不支持从CLI创建的用户！")

        self.user = user  # 存储查询到的用户对象
        if not user:
            raise wtforms.ValidationError("用户不存在！")
        else:
            #如果用户存在 则验证是否启用 user.enable是1表示启用 0表示未启用
            if not user.enable:
                raise wtforms.ValidationError("用户未启用，请联系管理员！")
            if user.enable != "1":
                raise wtforms.ValidationError("用户未启用，请联系管理员！")
            password = self.password.data
            print(password)
            if not check_password_hash(user.password, password):
                print(field.data)
                raise wtforms.ValidationError("密码错误！")





class PasswdForm(wtforms.Form):
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    new_password =  wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    confirmPassword = wtforms.StringField(validators=[EqualTo('new_password', message='密码输入不一致')])

    def validate_password(self,field):
        if not (check_password_hash(current_user.password, field.data)):
            raise wtforms.ValidationError("当前密码输入错误！")