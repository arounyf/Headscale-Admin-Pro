import sqlite3
import wtforms
from flask import session, current_app
from flask_login import current_user
from werkzeug.security import check_password_hash
from wtforms.validators import length, DataRequired, Regexp, Length, EqualTo, Email
from exts import SqliteDB
from models import User
from utils import check_account_locked, record_login_failure


class RegisterForm(wtforms.Form):
    vercode = wtforms.StringField(validators=[Length(min=4, max=4, message='验证码格式错误')])
    captcha_uuid = wtforms.StringField(validators=[Length(min=36, max=36, message='UUID错误')])
    username = wtforms.StringField(
        validators=[
            DataRequired(message='用户名不能为空'),
            Length(min=3, max=20, message='用户名长度需在3 - 20位之间'),
            Regexp(
                regex=r'^[a-zA-Z][a-zA-Z0-9]*$',
                message='用户名必须以字母开头，且只能包含字母和数字'
            )
        ]
    )
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    confirmPassword = wtforms.StringField(validators=[EqualTo('password',message='密码输入不一致')])
    phone = wtforms.StringField(validators=[DataRequired(),length(11, 11),Regexp(r'(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}', 0, '手机号码不合法')])
    email = wtforms.StringField(validators=[Email(message='请输入有效的电子邮件地址')])




    def validate_vercode(self,field):
        if current_app.config.get('EMAIL_VERIFY_REG') == 'on':
            code = session.pop('email_code', None)
            if not code or code != field.data:
                raise wtforms.ValidationError("邮箱验证码错误或已失效！")
        else:
            code = session.pop('code', None)
            if not code or code != field.data:
                raise wtforms.ValidationError("验证码错误或已失效！")


    def validate_password(self,field):
        if ' ' in field.data:
            raise wtforms.ValidationError('密码不能包含空格')


    def validate_username(self,field):
        if ' ' in field.data:
            raise wtforms.ValidationError('用户名不能包含空格')
        else:
            with SqliteDB() as cursor:
                cursor.execute("SELECT name FROM users WHERE name =?", (field.data,))
                cursor.row_factory = sqlite3.Row
                user_name = cursor.fetchone()
                if user_name:
                    raise wtforms.ValidationError(f"{user_name['name']} 用户已注册！")


    def validate_email(self,field):
        with SqliteDB() as cursor:
            cursor.row_factory = sqlite3.Row
            cursor.execute("SELECT email FROM users WHERE email =?", (field.data,))
            email = cursor.fetchone()
            if email:
                raise wtforms.ValidationError(f"{email['email']} 邮箱已被注册！")



class LoginForm(wtforms.Form):
    vercode = wtforms.StringField(validators=[Length(min=4, max=4, message='验证码格式错误')])
    captcha_uuid = wtforms.StringField(validators=[Length(min=36, max=36, message='UUID错误')])
    username = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='用户名格式错误')])
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])


    #user = None  # 用于存储查询到的用户对象
    def validate_vercode(self, field):
        code = session.pop('code', None)
        if not code or code != field.data:
            raise wtforms.ValidationError("验证码错误或已失效！")


    def validate_username(self, field):
        try:
            with SqliteDB() as cursor:
                query = """
                        SELECT id, name, created_at, updated_at,email, password,expire, cellphone, role, node, route, enable 
                        FROM users 
                        WHERE name =?
                        """
                cursor.execute(query, (field.data,))
                user_data = cursor.fetchone()
                if user_data:
                    user = User(*user_data)
                    self.user = user
                    # 检查账户是否已被锁定
                    is_locked, remaining = check_account_locked(field.data)
                    if is_locked:
                        raise wtforms.ValidationError(f"账户已锁定，请{remaining}分钟后再试")
                    input_password = self.password.data
                    if check_password_hash(user.password, input_password):
                        if user.enable == 0:
                            if current_app.config.get('EMAIL_VERIFY_REG') == 'on':
                                raise wtforms.ValidationError("请先验证邮箱后再登录，检查你的收件箱")
                            raise wtforms.ValidationError("账户已被禁用，请联系管理员")
                    else:
                        record_login_failure(field.data)
                        raise wtforms.ValidationError("密码错误！")
                else:
                    raise wtforms.ValidationError("用户不存在！")
                return True
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return False




class PasswdForm(wtforms.Form):
    password = wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    new_password =  wtforms.StringField(validators=[DataRequired(),Length(min=3,max=20,message='密码格式错误')])
    confirmPassword = wtforms.StringField(validators=[EqualTo('new_password', message='密码输入不一致')])

    def validate_password(self,field):
        if not (check_password_hash(current_user.password, field.data)):
            raise wtforms.ValidationError("当前密码输入错误！")