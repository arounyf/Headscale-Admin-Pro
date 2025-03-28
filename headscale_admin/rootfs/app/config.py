from datetime import timedelta

from sqlalchemy import event

SQLALCHEMY_DATABASE_URI = 'sqlite:////var/lib/headscale/db.sqlite'
SECRET_KEY = 'SFhkrGKQL2yB9F' # respose解码



BEARER_TOKEN = ''
PERMANENT_SESSION_LIFETIME = timedelta(seconds=3600)
SERVER_HOST = "http://127.0.0.1:8080"
TAILSCALE_UP_URL = "http://192.168.6.5:8080"
SERVER_NET = "eth0"




REGION ="<tr><td>1</td><td>四川</td><td>200 Mbps</td></tr><tr><td>2</td><td>浙江</td><td>200 Mbps</td></tr>"
