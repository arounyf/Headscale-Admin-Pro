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
