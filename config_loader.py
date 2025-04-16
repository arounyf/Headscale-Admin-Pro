import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
# 将配置项添加到 Flask 应用的配置中
SQLALCHEMY_DATABASE_URI = config.get('database', 'SQLALCHEMY_DATABASE_URI')
SECRET_KEY = config.get('security', 'SECRET_KEY')
BEARER_TOKEN = config.get('security', 'BEARER_TOKEN')
PERMANENT_SESSION_LIFETIME = int(config.get('session', 'PERMANENT_SESSION_LIFETIME'))
SERVER_HOST = config.get('server', 'SERVER_HOST')
TAILSCALE_UP_URL = config.get('server', 'TAILSCALE_UP_URL')
SERVER_NET = config.get('server', 'SERVER_NET')
REGION = config.get('region', 'REGION')