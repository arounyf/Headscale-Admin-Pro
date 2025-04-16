import yaml



# 读取 YAML 配置文件
with open('/etc/headscale/config.yaml', 'r') as file:
    config_yaml = yaml.safe_load(file)


# 配置
SECRET_KEY = 'SFhkrGKQL2yB9F'
PERMANENT_SESSION_LIFETIME = 3600
SERVER_HOST = 'http://127.0.0.1:8080'
REGION_HTML = "<tr><td>1</td><td>四川</td><td>200 Mbps</td></tr><tr><td>2</td><td>浙江</td><td>200 Mbps</td></tr>"



# 从 yaml 配置文件中获取配置项
SQLALCHEMY_DATABASE_URI =  "sqlite:///" + config_yaml.get('database', {}).get('sqlite', {}).get('path')

SERVER_NET = config_yaml.get('server_net', {})
BEARER_TOKEN = config_yaml.get('apikey', {})
SERVER_URL = config_yaml.get('server_url', {})

