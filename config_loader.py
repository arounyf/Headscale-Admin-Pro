from ruamel.yaml import YAML


# 创建 YAML 对象，设置保留注释
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

# 读取 YAML 配置文件
with open('/etc/headscale/config.yaml', 'r') as file:
    config_yaml = yaml.load(file)




# 配置
SECRET_KEY = 'SFhkrGKQL2yB9F'
PERMANENT_SESSION_LIFETIME = 3600
SERVER_HOST = 'http://127.0.0.1:8080'



# 从 yaml 配置文件中获取配置项
SERVER_URL = config_yaml.get('server_url', {})
SQLALCHEMY_DATABASE_URI =  "sqlite:///" + config_yaml.get('database', {}).get('sqlite', {}).get('path')

# 检查配置项是否存在，不存在则创建
if 'apikey' not in config_yaml:
    config_yaml['apikey'] = "vQ9Q4vK.yX14nC-qOVcRKJ56Z-v3HC_B2SGrAqun"
if 'server_net' not in config_yaml:
    config_yaml['server_net'] = "ens18"
if 'region_html' not in config_yaml:
    config_yaml['region_html'] = "<tr><td>1</td><td>四川</td><td>200 Mbps</td></tr><tr><td>2</td><td>浙江</td><td>200 Mbps</td></tr>"

# 将更新后的配置写回到文件
with open('/etc/headscale/config.yaml', 'w') as file:
    yaml.dump(config_yaml, file)


BEARER_TOKEN = config_yaml.get('apikey', {})
SERVER_NET = config_yaml.get('server_net', {})
REGION_HTML = config_yaml.get('region_html', {})
