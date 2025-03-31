from datetime import timedelta
import os
from sqlalchemy import event

SQLALCHEMY_DATABASE_URI = 'sqlite:////var/lib/headscale/db.sqlite'
SECRET_KEY = 'SFhkrGKQL2yB9F' # respose解码

def remove_quotes(value):
    # 去除两端的双引号和单引号
    value = value.strip('"').strip("'")
    # 替换字符串内的双引号和单引号为无（或根据需要替换为其他字符）
    return value.replace('"', '').replace("'", '')

BEARER_TOKEN = ''
PERMANENT_SESSION_LIFETIME = timedelta(seconds=3600)
SERVER_HOST = remove_quotes(os.getenv('SERVER_HOST', 'http://127.0.0.1:8080'))
TAILSCALE_UP_URL = remove_quotes(os.getenv('TAILSCALE_UP_URL', 'http://192.168.6.5:8080'))
SERVER_NET = remove_quotes(os.getenv('SERVER_NET', 'eth0'))




REGION ="<tr><td>1</td><td>四川</td><td>200 Mbps</td></tr><tr><td>2</td><td>浙江</td><td>200 Mbps</td></tr>"
