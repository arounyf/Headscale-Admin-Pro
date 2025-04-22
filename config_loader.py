from ruamel.yaml import YAML


# 创建 YAML 对象，设置保留注释
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

# 读取 YAML 配置文件
with open('/etc/headscale/config.yaml', 'r') as file:
    config_yaml = yaml.load(file)




# 配置定义
SECRET_KEY = 'SFhkrGKQL2yB9F'
PERMANENT_SESSION_LIFETIME = 3600
SERVER_HOST = 'http://127.0.0.1:8080'


DEFAULT_REG_DAYS = '7'


# 从 yaml 配置文件中获取headscale配置项
SERVER_URL = config_yaml.get('server_url', {})
NET_TRAFFIC_RECORD_FILE = '/var/lib/headscale/data.json'
SQLALCHEMY_DATABASE_URI =  "sqlite:///" + config_yaml.get('database', {}).get('sqlite', {}).get('path')


# 从 yaml 配置文件中获取WEB UI配置项
BEARER_TOKEN = config_yaml.get('apikey', {})
SERVER_NET = config_yaml.get('server_net', {})
REGION_HTML = config_yaml.get('region_html', {})
