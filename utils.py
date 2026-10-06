import json
import math
import os
import signal
import subprocess
import sys
import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import psutil

from flask import current_app, session
from ruamel.yaml import YAML
from datetime import datetime, timezone, timedelta
from exts import SqliteDB


# api接口返回格式定义
def res(code=None, msg=None, data=None):
    if code is None: code = '1'
    if msg is None: msg = "msg未初始化"
    if data is None: data = {}
    response = { "code": code,"msg": msg,"data": data}
    return response


def table_res(code=None, msg=None, data=None, count=None, total_row_count = None):
    if code is None: code = '1'
    if msg is None: msg = "msg未初始化"
    if data is None: data = {}
    if count is None: count = 0
    if total_row_count is None: total_row_count = 0

    response = {
        'code': code,
        'msg': msg,
        'data': data,
        'count': count,
        'totalRow': {
            'count': total_row_count
        }
    }
    return response


def to_request(method,url_path,data=None,flag = True):
    server_host = current_app.config['SERVER_HOST']
    bearer_token = current_app.config['BEARER_TOKEN']
    headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    url = server_host+url_path

    request_method = getattr(requests, method.lower())
    response = request_method(url, headers=headers, json=data, verify=False)

    if current_app.debug:
        print(f'{method} {url} -> {response.status_code}')


    # 如果返回Unauthorized则自动刷新apikey
    if response.text == "Unauthorized" and flag:
        refresh_result = to_refresh_apikey()
        if refresh_result['code'] == '0':
            current_app.config['BEARER_TOKEN'] = refresh_result['data']
            return to_request(method, url_path, data, False)
        else:
            return res('1', 'apikey刷新失败', '')

    if not response.ok:
        return res(str(response.status_code), response.text)

    return res('0', '请求成功', response.text)







# ---- 面板的时间约定 ----
#
# **库里一律存绝对时刻**：任何写进 db.sqlite 的时间值都必须带时区偏移
# （'2026-10-06 13:25:40+08:00'，或 UTC 的 '...Z'）。这不是风格偏好 —— 它让
# 「这一列是谁写的」不再影响怎么读，调用点也就不需要各自判断形态了。
#
# 写入方：
#   headscale(Go/GORM)  自己写带偏移的值。面板**不再插手** users.created_at /
#                       users.updated_at —— 以前面板按自己的格式覆盖它们，而
#                       headscale 读回那一行时按 time.Time 解析，裸值被当成 UTC，
#                       于是面板建的用户 createdAt 晚 8 小时。详见 auth.py。
#   面板                只剩两个自有列：users.expire、log.created_at，也必须带偏移
#                       （见本文件 record_log、blueprints/user.py 的 re_expire）。
#
# 读取只有一个入口：display_ts()，绑定下面的 PANEL_TZ_OFFSET，输出北京墙钟。
#
# strftime 的陷阱（老代码两个方向都错一半的原因）：它见到带偏移的输入会**先折成
# UTC** 再输出，于是
#
#   strftime('%Y-%m-%d %H:%M:%S', created_at)              对带偏移的行少 8 小时
#   strftime('%Y-%m-%d %H:%M:%S', created_at, 'localtime') 对裸值的行多 8 小时
#
# 所以 display_ts 得自己判断该不该加偏移，见下面那个 CASE。
#
# SQL 之外的显示格式化另有两处，都在边界上转 PANEL_TZ，改时记得跟 PANEL_TZ_OFFSET 对齐：
#   预认证密钥 —— 走 API 读，见 blueprints/preauthkey.py；反向发出去的值用
#                 datetime.now(timezone.utc)（跨 API 边界必须是真 UTC）
#   headscale 构建时间 —— 见本文件 _localize_build_time
# 显示时区的**唯一来源**。要改时区只改这一行 —— 另外两个写法都从它算出来：
#   PANEL_TZ_OFFSET  SQL 用（strftime 修饰符，'+8 hours'）
#   PANEL_TZ_ISO     前端用（ISO 偏移串，'+08:00'，经 app.py 的 /panel-tz.js 下发）
#
# 改这里会牵动 display_ts 里那个 CASE 的前提（它的 ELSE 分支假设裸值就是这个时区
# 的墙钟）。库里还有裸值时不要改 —— 判据见 find_bare_time_values()。
PANEL_TZ = timezone(timedelta(hours=8))


def _tz_sql_offset(tz):
    """timezone → SQLite strftime 修饰符，如 '+8 hours'。

    半小时时区不能用 '5 hours 30 minutes' 这种写法：SQLite 把整个字符串当成**一个**
    修饰符，认不出来时返回 NULL 而不是报错 —— 整列时间会静默变成空。半小的偏移改发
    'N minutes'（实测 '+330 minutes' 正确）。现在的 +8 走整小时分支，不受影响。
    """
    minutes = int(tz.utcoffset(None).total_seconds()) // 60

    if minutes % 60 == 0:
        return '{0:+d} hours'.format(minutes // 60)

    return '{0:+d} minutes'.format(minutes)


def _tz_iso_offset(tz):
    """timezone → ISO 偏移串，如 '+08:00'（前端拼 ISO 时间用）。"""
    minutes = int(tz.utcoffset(None).total_seconds()) // 60
    sign = '+' if minutes >= 0 else '-'
    hours, mins = divmod(abs(minutes), 60)
    return '{0}{1:02d}:{2:02d}'.format(sign, hours, mins)


PANEL_TZ_OFFSET = _tz_sql_offset(PANEL_TZ)
PANEL_TZ_ISO = _tz_iso_offset(PANEL_TZ)


# 允许出现「裸值」（不带时区偏移）的列。
#
# display_ts 里那个 CASE 的 ELSE 分支假设「没有偏移的值 = 面板显示时区的墙钟」。
# 这个假设**只对旧面板写过的列成立** —— 那几列的历史行真的是裸的北京墙钟。
#
# headscale 写的列永远带偏移，对它们来说裸值是**不该存在的东西**：一旦出现就是
# 代码坏了，而那个 ELSE 分支会安静地猜一个可能错 8 小时的值、不报错（当初那个
# +8 小时的 bug 就是这么活了很久的）。所以列名必须在这张表里，不在就抛。
#
# 加新列进来之前先问：这一列的历史值真的可能是裸的吗？答不上来就别加 ——
# 读 headscale 的时间应该走 API + api_ts。
#
# 不带表名的列名默认属于 users（现有调用点查的都只有 users 表）。
BARE_TOLERANT_COLUMNS = {
    'users.created_at', 'users.updated_at', 'users.expire', 'log.created_at',
}


def display_ts(column):
    """生成「把 <column> 显示成北京墙上时间」的 SQL 片段。理由见上面那条约定。

    对带偏移的值（headscale 写的）和裸值（面板旧版本写的）都正确 —— 那个 CASE 是
    **迁移 shim**：纯 '+8 hours' 会把裸值当 UTC 读、多显示 8 小时。'YYYY-MM-DD
    HH:MM:SS' 恰好 19 字符，所以**第 19 位之后出现的 '+'/'-' 只可能是时区偏移**
    （日期的短横线都在前 10 位内），裸值分支不位移，因为面板旧版本写下的
    users.expire / users.created_at 本来就是北京墙钟。

    **不要把这个 CASE 收成常量。** 12 的库清干净了不代表生产干净 —— 生产还留着旧
    面板写下的裸值，收掉会让它们集体多显示 8 小时。要收的前提是**生产**也零裸值。

    另：这个 CASE 的容忍是有代价的 —— 将来谁再写进一个裸值，不会报错，只会静默
    显示错 8 小时。所以写库那头必须带偏移（本文件 record_log、blueprints/auth.py、
    blueprints/user.py 的 re_expire 三个写入点）。

    column 必须是代码里写死的列名（可带表前缀），不能来自请求；且必须在
    BARE_TOLERANT_COLUMNS 里（见那张表上面的理由）。
    """
    key = column if '.' in column else 'users.' + column

    if key not in BARE_TOLERANT_COLUMNS:
        raise ValueError(
            "display_ts 不接受 {0!r}：它不在「历史值可能是裸值」的列清单里（{1}）。"
            'headscale 拥有的列永远带偏移，裸值出现即代码有错，不该在这里猜一个值。'
            '读 headscale 的时间请走 API + api_ts。'.format(
                column, ' / '.join(sorted(BARE_TOLERANT_COLUMNS)))
        )

    return _display_ts_sql(column)


def _display_ts_sql(column):
    """display_ts 的实际实现，不做列名检查（自检也要用它，那里传的是字面量）。"""
    offset = (
        "CASE WHEN instr(substr({0},20),'+')>0"
        " OR instr(substr({0},20),'-')>0"
        " OR substr({0},-1)='Z'"
        " THEN '{1}' ELSE '0 hours' END"
    ).format(column, PANEL_TZ_OFFSET)
    return "strftime('%Y-%m-%d %H:%M:%S', {0}, {1})".format(column, offset)


def api_ts(value):
    """把 headscale API 返回的时间串转成 display_ts 同款格式的北京墙钟串。

    display_ts 管走库那一侧，这个管走 API 那一侧。两条路的输出必须一模一样，
    否则同一个字段在「读库的页」和「读 API 的页」上会长得不一样。

    别在调用点自己写 fromisoformat + astimezone：这一句里藏着坑（3.11 之前的
    fromisoformat 不认结尾的 Z），抄错一次就静默差 8 小时 —— 这正是老 local_ts
    那类 bug 的来源。空值返回 ''。
    """
    if not value:
        return ''

    when = datetime.fromisoformat(str(value).replace('Z', '+00:00'))

    return when.astimezone(PANEL_TZ).strftime('%Y-%m-%d %H:%M:%S')


# 库里所有时间列。表名 → 列名。加新时间列时记得往这里加，否则扫描漏。
TIME_COLUMNS = {
    'users': ('created_at', 'updated_at', 'expire'),
    'nodes': ('created_at', 'updated_at', 'last_seen', 'expiry'),
    'log': ('created_at',),
    'pre_auth_keys': ('created_at', 'expiration'),
    'api_keys': ('created_at', 'expiration'),
}


def absolute_ts(when):
    """把 datetime 编成能进库的串，并**挡住不带时区的值**。

    这是「库里一律存绝对时刻」这条约定的唯一关口。裸值一旦进库，不会被任何地方
    报错 —— display_ts 的 shim 会把它当成 PANEL_TZ 的墙钟**静默放过** —— 所以只能
    在这里拦。三个写入点（record_log / auth.py 注册 / user.py 的 re_expire）都走它。
    """
    if when.utcoffset() is None:
        raise ValueError(
            '禁止把裸时间写进库：{0!r}。用 datetime.now(timezone.utc)，或对墙钟值做 '
            '.replace(tzinfo=PANEL_TZ)。约定见 utils.py 顶部。'.format(when)
        )

    return when.isoformat(sep=' ')


def find_bare_time_values():
    """扫描库里所有时间列，返回裸值清单 [(表, 列, 行数)]。空列表 = 不变量成立。

    这就是验收判据本身：**全库零裸值 ⟺ display_ts 对每一列都正确**，两者是同一
    件事。'YYYY-MM-DD HH:MM:SS' 恰好 19 字符，所以第 19 位之后出现 '+'/'-'、或
    结尾是 'Z' 的，才是带偏移的绝对时刻。

    扫描只报告不修数据；缺表/缺列（老库或 headscale 版本差异）直接跳过。
    """
    found = []
    with SqliteDB() as cursor:
        for table, cols in TIME_COLUMNS.items():
            for col in cols:
                sql = (
                    "SELECT COUNT(*) AS n FROM {0} WHERE {1} IS NOT NULL"
                    " AND {1} != ''"
                    " AND instr(substr({1},20),'+') = 0"
                    " AND instr(substr({1},20),'-') = 0"
                    " AND substr({1},-1) != 'Z'"
                ).format(table, col)
                try:
                    row = cursor.execute(sql).fetchone()
                except Exception:
                    continue

                if row and row['n']:
                    found.append((table, col, row['n']))

    return found


def check_display_ts():
    """自检 display_ts 的 SQL 与 PANEL_TZ 是否一致，返回错误描述或 None（=通过）。

    为什么需要：PANEL_TZ_OFFSET 是拼进 SQL 的字符串，写错不会抛异常。SQLite 认不出
    修饰符时返回 NULL —— 所有时间列会静默变成空，页面上一片空白而不是报错。这里跑
    一次已知输入的换算，把期望值用 **Python 的时区算术**独立算出来对答案，因此它同时
    验证了「SQL 修饰符合法」和「SQL 与 Python 两条路算出的偏移一致」。
    """
    sql = "SELECT {0} AS t".format(_display_ts_sql("'2026-01-01 00:00:00+00:00'"))
    expected = (
        datetime(2026, 1, 1, tzinfo=timezone.utc)
        .astimezone(PANEL_TZ)
        .strftime('%Y-%m-%d %H:%M:%S')
    )

    with SqliteDB() as cursor:
        try:
            got = cursor.execute(sql).fetchone()['t']
        except Exception as e:
            return 'display_ts 的 SQL 跑不起来：{0}（{1}）'.format(e, sql)

    if got != expected:
        return (
            "display_ts 自检不符：UTC 2026-01-01 00:00:00 期望显示 {0!r}，实际 {1!r}"
            '（PANEL_TZ_OFFSET={2!r}）'.format(expected, got, PANEL_TZ_OFFSET)
        )

    return None


def record_log(user_id, log_content):
    try:
        with SqliteDB() as cursor:
            # 存 UTC 绝对时刻，由 display_ts 统一换算成北京墙钟。走 absolute_ts
            # 是为了让「忘了带时区」当场炸掉，而不是写进去之后静默差 8 小时。
            current_time = absolute_ts(datetime.now(timezone.utc))
            cursor.execute(
                "INSERT INTO log (user_id, content, created_at) VALUES (?,?,?);",
                (user_id, log_content, current_time)
            )
            return True
    except Exception as e:
        print(f"记录日志失败: {e}")
        return False



# 获取流量、cpu、内存使用情况
def get_sys_info():
    cpu_usage = psutil.cpu_percent()

    memory_info = psutil.virtual_memory()
    memory_usage_percent = memory_info.percent

    recv = {}
    sent = {}
    

    net_interface = current_app.config['SERVER_NET']
    data = psutil.net_io_counters(pernic=True)
    interfaces = data.keys()
    
    sent_speed = recv_speed = 0

    for interface in interfaces:
        #print(interface)
        if interface == net_interface:  # 只处理 ens18 网卡
            sent.setdefault(interface, data.get(interface).bytes_sent)
            recv.setdefault(interface, data.get(interface).bytes_recv)

            sent_speed = math.ceil(sent.get(net_interface) / 1024)
            recv_speed = math.ceil(recv.get(net_interface) / 1024)

    info_dict = {
        'cpu_usage': cpu_usage,
        'memory_usage_percent': memory_usage_percent,
        'sent_speed': sent_speed,
        'recv_speed': recv_speed
    }

    return json.dumps(info_dict)




# 记录最新的25个流量记录
def get_data_record():
    json_data_now = json.loads(get_sys_info())

    recv_speed = str(json_data_now["recv_speed"])
    sent_speed = str(json_data_now["sent_speed"])

    with open(current_app.config['NET_TRAFFIC_RECORD_FILE'], 'r') as file:
        content = file.read()
        json_data_local = json.loads(content)

        keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y']
        for i in range(len(keys) - 1):
            json_data_local['sent'][keys[i]] = json_data_local['sent'][keys[i + 1]]
            json_data_local['recv'][keys[i]] = json_data_local['recv'][keys[i + 1]]

        json_data_local["sent"]["y"] = sent_speed
        json_data_local["recv"]["y"] = recv_speed

    with open(current_app.config['NET_TRAFFIC_RECORD_FILE'], 'w') as file:
        json.dump(json_data_local, file, indent=4)

    return json_data_local




def _headscale_serve_pids():
    """返回 argv 恰好是 `headscale serve` 的进程 PID 列表。

    替换原来的
    `ps -ef | grep -E 'headscale serve' | grep -v grep | awk '{print $2}' | tail -n 1`：
      * `tail -n 1` 在多实例时等于随机挑最后一个，而不是挑面板管的那个；
      * `grep -E` 是子串匹配，`sh -c "headscale serve"` 这类包装进程也会命中；
      * 精确比对 argv 还顺带排除了带 `-c <别的配置>` 手工起的实例 ——
        start_headscale 是用 subprocess.Popen(['headscale', 'serve']) 拉起来的
        （不带 -c），所以"面板管的那个"就是无参数的那个。

    这里不用 docker API（容器没挂 docker socket）也不用 systemd（容器内没有 init）。
    """
    pids = []
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] == ['headscale', 'serve']:
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(pids)


def _signal_headscale(sig, ok_msg):
    """给面板管的 headscale 进程发信号。"""
    pids = _headscale_serve_pids()
    if not pids:
        return res('1', '未检测到 headscale 进程')

    failed = []
    for pid in pids:
        try:
            os.kill(pid, sig)
        except OSError as e:
            failed.append(f'{pid}: {e}')

    if failed:
        return res('1', f"发送信号失败：{'; '.join(failed)}")

    return res('0', ok_msg, f'已向 {len(pids)} 个进程发送信号：{pids}')


def reload_headscale():
    return _signal_headscale(signal.SIGHUP, '执行成功')



def get_server_net():
    try:
        # 执行系统命令获取网卡信息
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, check=True)
        output = result.stdout

        # 解析输出结果，提取网卡名
        interfaces = []
        for line in output.split('\n'):
            if line.strip().startswith('1:') or line.strip().startswith('2:'):
                # 提取网卡名
                interface = line.split(':')[1].strip()
                interfaces.append(interface)

        return {'network_interfaces': interfaces}
    except subprocess.CalledProcessError as e:
        return {'error': f'执行命令时出错: {e.stderr}'}, 500
    except Exception as e:
        return {'error': f'发生未知错误: {str(e)}'}, 500



def start_headscale():
    _forget_headscale_version()
    log_file_path = os.path.join('/var/lib/headscale', 'headscale.log')

    if get_headscale_pid():
        return  res('0', '检测到headscale已启动')

    try:
        with open(log_file_path, 'a') as log_file:
            # 启动 headscale serve 进程，并将标准输出和标准错误输出重定向到日志文件
            subprocess.Popen(['headscale', 'serve'], stdout=log_file, stderr=log_file)
        return res('0', '启动成功')
    except Exception as e:
        return res('1', f'启动失败: {str(e)}')


def stop_headscale():
    _forget_headscale_version()
    return _signal_headscale(signal.SIGTERM, '停止成功')


def get_headscale_pid():
    """返回面板管的 headscale PID；没在跑时返回 False。"""
    pids = _headscale_serve_pids()
    if not pids:
        return False
    print(f"headscale pid is {pids[0]}")
    return pids[0]

_headscale_version = None


def _forget_headscale_version():
    """丢掉版本号缓存。headscale 二进制被换掉之后必须重新查。"""
    global _headscale_version
    _headscale_version = None


def _localize_build_time(raw):
    """把 `headscale version` 里的 build time 从 UTC 换成本地时区。

    这个戳是 CI 用 `date -u` 打的，二进制报出来的必然带 Z —— 是个从外面进来的
    UTC 值，而库里和界面上其余的时间都是容器本地（见上面「面板的时间约定」）。
    不转的话悬停框里显示 03:39，看的人得自己知道那是 UTC 再减 8 小时才对得上
    墙上时钟。

    输出改成 `2026-10-06 11:39:25 +0800` —— 把偏移显式写出来，而不是留一个
    要靠读者知道含义的 Z。用哪个时区由容器的 TZ 决定（docker-compose 里是
    Asia/Shanghai），和面板其余部分一致。

    解析不了就原样返回：直接 `docker build` 出来的二进制这一行是 `unknown`，
    一个显示问题不值得把那行吞掉。
    """
    if not raw:
        return raw
    lines = []
    for line in raw.splitlines():
        if line.startswith('build time:'):
            value = line.split(':', 1)[1].strip()
            try:
                # 早于 3.11 的 fromisoformat 不认结尾那个 Z，先换掉，省得
                # 为一行显示依赖解释器版本。
                when = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                lines.append(line)
                continue
            if when.tzinfo is None:
                lines.append(line)
                continue
            # 用 PANEL_TZ 而不是裸 .astimezone()：显示时区应当是面板的常量，不是
            # 容器 TZ 的隐式属性（换环境就会跟别的页面显示不一致）。
            line = 'build time: ' + when.astimezone(PANEL_TZ).strftime('%Y-%m-%d %H:%M:%S %z')
        lines.append(line)
    return '\n'.join(lines)


def get_headscale_version():
    """headscale 版本号，查一次就缓存。

    `headscale version` 不依赖 serve 进程，启动时就能拿到，没必要每个请求都
    fork 一次 —— 首页、设置页、关于弹窗都要显示它。

    缓存唯一的失效点是二进制被换掉：12 和生产的升级方式都是热替换
    /app/headscale 后重启 headscale 进程，面板本身不重启。所以 start/stop
    两个入口各清一次，否则关于页会一直报换之前那个版本。

    返回的是命令的完整输出，四行；其中 build time 已经过
    [_localize_build_time] 换成本地时区。缓存里存的仍是原样输出 —— 转换只
    发生在显示这一层，`headscale version` 本身报什么不受影响。
    """
    global _headscale_version
    if _headscale_version is None:
        try:
            command = "headscale version"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            _headscale_version = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print({e.stderr})
    return _localize_build_time(_headscale_version)


def get_headscale_version_line():
    """只要版本号那一行，形如 `headscale v0.29.4-hs`。

    `headscale version` 的四行里只有第一行是版本号，另外三行是 commit、
    build time、built with。**只给「关于」弹窗用** —— 那里是一段正文，
    摆四行 detail 会把版面撑得很碎。

    导航条的「运行中」tooltip 和设置页的 tips 用的是完整的
    [get_headscale_version]：那两处是悬停才出现的浮层，commit 和 build
    时间正好是排查「12 上跑的到底是哪个构建」时要看的东西，收短就没有了。
    """
    raw = get_headscale_version()
    if not raw:
        return ''
    # 第一行形如 "headscale version v0.29.4-hs"，去掉中间的 version。
    return raw.splitlines()[0].strip().replace('headscale version ', 'headscale ', 1)

def save_config_yaml(config_dict):
    # 创建 YAML 对象，设置保留注释
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    # 读取 YAML 配置文件

    with open('/etc/headscale/config.yaml', 'r') as file:
        config_yaml = yaml.load(file)

    for key, value in config_dict.items():
        current_app.config[key] = value
        config_yaml[key.lower()] = value

        # 将更新后的配置写回到文件
    with open('/etc/headscale/config.yaml', 'w') as file:
        yaml.dump(config_yaml, file)


    return res('0', '修改成功', '')





def to_refresh_apikey():
    try:
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)
        apikey = result.stdout.strip()
        config_mapping = {
            'BEARER_TOKEN': apikey
        }
        save_config_yaml(config_mapping)
        code, msg, data = '0','获取apikey成功',apikey
    except subprocess.CalledProcessError as e:
        code, msg, data = '1', '执行失败', f"错误信息：{e.stderr}"

    return res(code, msg, data)



def get_headscale_status(app):
    """
    检查 headscale 的健康状态。
    如果启动失败，抓取并显示本次启动尝试产生的所有日志。
    """
    with app.app_context():
        url = current_app.config['SERVER_HOST'] + '/health'
        log_file_path = '/var/lib/headscale/headscale.log'

    # 记录日志文件初始大小
    log_start_pos = 0
    if os.path.exists(log_file_path):
        try:
            log_start_pos = os.path.getsize(log_file_path)
        except OSError as e:
            print(f"Warning: Could not get size of log file: {e}")

    print(f"Health check started. Monitoring log file from position: {log_start_pos}")

    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(url, timeout=2, verify=False)
            if response.status_code == 200 and response.json() == {"status": "pass"}:
                print("Success: Headscale is healthy and running.")
                return True
            else:
                print(f"Attempt {attempt + 1} failed. Status code: {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"Attempt {attempt + 1}/{max_attempts}: Headscale not ready yet...")

        attempt += 1
        time.sleep(1)

    # 从初始位置读取新日志
    print("\n" + "="*60)
    print("Error: Headscale failed to start properly.")
    print("="*60)
    print("Fetching all logs since health check started:")
    print("-" * 60)

    startup_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(log_start_pos)
                startup_logs = f.readlines()
        except OSError as e:
            print(f"Error reading log file: {e}")
    else:
        print(f"Error: Log file not found at: {log_file_path}")

    if startup_logs:
        # 打印所有新日志，并设置为红色
        for line in startup_logs:
            # \033[91m 开启红色，\033[0m 恢复默认颜色
            print("\033[91m" + line.strip() + "\033[0m")
    else:
        print("Warning: No new logs were generated during the health check.")
        print("This could mean headscale didn't start at all or the log path is incorrect.")

    print("="*60)
    print("Suggestions:")
    print(f"1. Check the full log for more context: `tail -n 200 {log_file_path}`")
    print("2. Verify the database migrations and integrity.")
    print("="*60)

    sys.exit(1)


def to_init_db(app):
    get_headscale_status(app)
    _init_app_tables()


# ---- 应用自定义表初始化 ----

def _init_app_tables():
    pass


# ---- 邮件发送 ----

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer


def _get_token_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='email-token')


def generate_email_token(user_id):
    """生成签名令牌，1小时有效，不存数据库"""
    return _get_token_serializer().dumps(user_id)


def verify_email_token(token):
    """验证签名令牌，返回 user_id 或 None"""
    try:
        return _get_token_serializer().loads(token, max_age=3600)
    except Exception:
        return None


def send_email(to_email, subject, body):
    host = current_app.config.get('SMTP_HOST', '')
    port = int(current_app.config.get('SMTP_PORT', '465'))
    user = current_app.config.get('SMTP_USER', '')
    password = current_app.config.get('SMTP_PASSWORD', '')
    from_addr = current_app.config.get('SMTP_FROM', user)
    from_name = current_app.config.get('SMTP_FROM_NAME', '')
    use_ssl = str(current_app.config.get('SMTP_SSL', 'true')).lower() in ('true', '1', 'yes', 'on')

    if not host or not user or not password:
        print('SMTP not configured, skip sending email')
        return False

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        print(f'SMTP connecting: {host}:{port} SSL={use_ssl} user={user}')
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=10) as s:
                s.login(user, password)
                s.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as s:
                s.starttls()
                s.login(user, password)
                s.sendmail(from_addr, [to_email], msg.as_string())
        print(f'Email sent to {to_email}')
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f'SMTP 认证失败: {e}')
        return False
    except Exception as e:
        print(f'Send email failed: {type(e).__name__}: {e}')
        return False




# ---- IP 地理位置 ----

import requests as _requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_IP_CACHE_FILE = '/var/lib/headscale/ip_locations.json'


def _load_ip_cache():
    if os.path.exists(_IP_CACHE_FILE):
        try:
            with open(_IP_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_ip_cache(data):
    try:
        with open(_IP_CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def _is_private_ip(ip):
    """判断是否为内网/私有IP"""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback
    except ValueError:
        return ip.lower() in ('localhost',)



def get_ip_location(ip):
    """查询IP地理位置，JSON文件缓存。根据IP_API_SOURCE配置选择API"""
    from flask import current_app as ca
    source = ca.config.get('IP_API_SOURCE', 'none')
    if source == 'none':
        return ''
    if _is_private_ip(ip):
        return '内网IP'

    cache = _load_ip_cache()
    if ip in cache:
        return cache[ip]

    loc = ''
    if source == 'tianapi':
        loc = _query_tianapi(ip)
    elif source == 'ipapi':
        loc = _query_ipapi(ip)
    if not loc:
        return ''

    cache[ip] = loc
    _save_ip_cache(cache)
    return loc


def _query_tianapi(ip):
    from flask import current_app as ca
    api_key = ca.config.get('TIANAPI_KEY', '')
    if not api_key:
        return ''
    try:
        resp = _requests.get('https://apis.tianapi.com/ipquery/index',
                             params={'key': api_key, 'ip': ip, 'full': 1}, timeout=5)
        data = resp.json()
        if data.get('code') == 200:
            r = data['result']
            return f"{r.get('country','')} {r.get('province','')} {r.get('city','')} {r.get('district','')} {r.get('isp','')}"
    except Exception as e:
        print(f'[_query_tianapi] error: {e}')
    return ''


def _query_ipapi(ip):
    try:
        resp = _requests.get(f'http://ip-api.com/json/{ip}?lang=zh-CN', timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                return f"{data.get('country','')} {data.get('regionName','')} {data.get('city','')}"
    except Exception:
        pass
    return ''


# ---- 登录 IP 记录已合并到 record_log ----


# 账户锁定：连续 5 次登录失败后锁定 30 分钟
_LOGIN_FAILURES_FILE = '/var/lib/headscale/login_failures.json'
_MAX_LOGIN_FAILURES = 5
_LOCKOUT_MINUTES = 30


def _load_login_failures():
    if os.path.exists(_LOGIN_FAILURES_FILE):
        try:
            with open(_LOGIN_FAILURES_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_login_failures(data):
    try:
        with open(_LOGIN_FAILURES_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def check_account_locked(username):
    """返回 (is_locked, remaining_minutes)"""
    data = _load_login_failures()
    entry = data.get(username)
    if not entry or not entry.get('locked_until'):
        return False, 0
    try:
        until = datetime.fromisoformat(entry['locked_until'])
        if datetime.now() < until:
            remaining = int((until - datetime.now()).total_seconds() / 60) + 1
            return True, remaining
    except (ValueError, TypeError):
        pass
    return False, 0


def record_login_failure(username):
    data = _load_login_failures()
    entry = data.get(username, {'failures': 0, 'locked_until': None})
    # 如果锁定已过期，重置计数器
    if entry.get('locked_until'):
        try:
            if datetime.now() >= datetime.fromisoformat(entry['locked_until']):
                entry = {'failures': 0, 'locked_until': None}
        except (ValueError, TypeError):
            entry = {'failures': 0, 'locked_until': None}
    entry['failures'] = entry.get('failures', 0) + 1
    if entry['failures'] >= _MAX_LOGIN_FAILURES:
        entry['locked_until'] = (datetime.now() + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
    data[username] = entry
    _save_login_failures(data)


def reset_login_failures(username):
    data = _load_login_failures()
    if username in data:
        del data[username]
        _save_login_failures(data)


# ---- 用户模式 ----

def is_user_mode():
    """管理员切换到用户视角，只看自己的数据"""
    from flask_login import current_user
    return session.get('user_mode') == 'user' and current_user.role == 'manager'
    