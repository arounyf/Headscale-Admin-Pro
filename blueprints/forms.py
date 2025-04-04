import wtforms
from flask import session
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms.validators import  length, DataRequired, Regexp, Length, EqualTo
from sqlalchemy import  text
from exts import db
from models import UserModel


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
        user = UserModel.query.filter_by(name=field.data).first()
        print(user)
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
            user = UserModel.query.filter_by(name=field.data).first()
        except Exception as e:
            if (type(e).__name__ == "ValueError"):
                raise wtforms.ValidationError("不支持从CLI创建的用户！")
                user = UserModel.query.filter_by(name=field.data).first()



        self.user = user  # 存储查询到的用户对象
        if not user:
            raise wtforms.ValidationError("用户不存在！")
        else:
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