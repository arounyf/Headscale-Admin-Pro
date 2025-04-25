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



# 从 yaml 配置文件中获取headscale配置项
SERVER_URL = config_yaml.get('server_url', {})
NET_TRAFFIC_RECORD_FILE = '/var/lib/headscale/data.json'
SQLALCHEMY_DATABASE_URI =  "sqlite:///" + config_yaml.get('database', {}).get('sqlite', {}).get('path')
ACL_PATH = "/etc/headscale/"+config_yaml.get('policy', {}).get('path')

# 从 yaml 配置文件中获取WEB UI配置项
BEARER_TOKEN = config_yaml.get('bearer_token', {})
SERVER_NET = config_yaml.get('server_net', {})
REGION_HTML = config_yaml.get('region_html', '<tr>'
                                             '<td>1</td><td>四川</td><td>200 Mbps</td></tr>'
                                             '<tr><td>2</td><td>浙江</td><td>200 Mbps</td><'
                                             '/tr>')
DEFAULT_REG_DAYS = config_yaml.get('default_reg_days', '7')
DEFAULT_NODE_COUNT = config_yaml.get('default_node_count', 2)
OPEN_USER_REG = config_yaml.get('open_user_reg', 'on')
REGION_DATA = config_yaml.get('region_data', '[{"name":"西藏", "value":0},'
            '{"name":"青海", "value":0},'
            '{"name":"宁夏", "value":0},'
            '{"name":"海南", "value":0},'
            '{"name":"甘肃", "value":0},'
            '{"name":"贵州", "value":0},'
            '{"name":"新疆", "value":0},'
            '{"name":"云南", "value":0},'
            '{"name":"重庆", "value":0},'
            '{"name":"吉林", "value":0},'
            '{"name":"山西", "value":0},'
            '{"name":"天津", "value":0},'
            '{"name":"江西", "value":0},'
            '{"name":"广西", "value":0},'
            '{"name":"陕西", "value":0},'
            '{"name":"黑龙江", "value":0},'
            '{"name":"内蒙古", "value":0},'
            '{"name":"安徽", "value":0},'
            '{"name":"北京", "value":0},{'
            '"name":"福建", "value":0},'
            '{"name":"上海", "value":0},'
            '{"name":"湖北", "value":0},'
            '{"name":"湖南", "value":0},'
            '{"name":"四川", "value":200},'
            '{"name":"辽宁", "value":0},'
            '{"name":"河北", "value":0},'
            '{"name":"河南", "value":0},'
            '{"name":"浙江", "value":200},'
            '{"name":"山东", "value":0},'
            '{"name":"江苏", "value":0},'
            '{"name":"广东", "value":0}]')
