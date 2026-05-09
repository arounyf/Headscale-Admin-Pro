import os
import uuid
from pathlib import Path

from ruamel.yaml import YAML


# 创建 YAML 对象，设置保留注释
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

# 读取 YAML 配置文件
with open('/etc/headscale/config.yaml', 'r') as file:
    config_yaml = yaml.load(file)


# SECRET_KEY 优先从环境变量读取，其次从持久化文件读取，最后自动生成
_SECRET_KEY_FILE = Path('/var/lib/headscale/.secret_key')


def _load_or_create_secret_key():
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    if _SECRET_KEY_FILE.exists():
        return _SECRET_KEY_FILE.read_text().strip()
    new_key = uuid.uuid4().hex + uuid.uuid4().hex
    _SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_KEY_FILE.write_text(new_key)
    return new_key


SECRET_KEY = _load_or_create_secret_key()
PERMANENT_SESSION_LIFETIME = 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('HTTPS', '').lower() in ('true', '1', 'on', 'yes')

listen_addr = config_yaml.get('listen_addr', '0.0.0.0:8080') 
_, port_str = listen_addr.rsplit(':', 1)
SERVER_HOST = f'http://127.0.0.1:{port_str}'  #从headscale配置文件中获取端口号，内部通信使用



# 从 yaml 配置文件中获取headscale配置项

SERVER_URL = config_yaml.get('server_url', {})
DATABASE_URI =  config_yaml.get('database', {}).get('sqlite', {}).get('path')
ACL_PATH = "/etc/headscale/"+config_yaml.get('policy', {}).get('path')




# 从 yaml 配置文件中获取WEB UI配置项
NET_TRAFFIC_RECORD_FILE = '/var/lib/headscale/data.json'
BEARER_TOKEN = config_yaml.get('bearer_token', {})
SERVER_NET = config_yaml.get('server_net', {})

DEFAULT_REG_DAYS = config_yaml.get('default_reg_days', '7')
DEFAULT_NODE_COUNT = config_yaml.get('default_node_count', 2)
OPEN_USER_REG = config_yaml.get('open_user_reg', 'on')

# SMTP 邮件配置
SMTP_HOST = config_yaml.get('smtp_host', '')
SMTP_PORT = config_yaml.get('smtp_port', '465')
SMTP_USER = config_yaml.get('smtp_user', '')
SMTP_PASSWORD = config_yaml.get('smtp_password', '')
SMTP_FROM = config_yaml.get('smtp_from', '')
SMTP_FROM_NAME = config_yaml.get('smtp_from_name', '')
SMTP_SSL = config_yaml.get('smtp_ssl', 'true')

# 邮箱验证注册开关
EMAIL_VERIFY_REG = config_yaml.get('email_verify_reg', 'off')
TIANAPI_KEY = config_yaml.get('tianapi_key', '')
IP_API_SOURCE = config_yaml.get('ip_api_source', 'none')
