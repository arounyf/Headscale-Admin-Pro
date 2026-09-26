import subprocess
from flask_login import login_required
from exts import SqliteDB
from login_setup import role_required
from flask import Blueprint, request, current_app, session
from utils import start_headscale, stop_headscale, save_config_yaml, res


bp = Blueprint("set", __name__, url_prefix='/api/set')




@bp.route('/upset' , methods=['GET','POST'])
@login_required
@role_required("manager")
def upset():
    form_fields = {
        'BEARER_TOKEN': 'apiKey',
        'SERVER_NET': 'serverNet',
        'SERVER_URL': 'serverUrl',
        'ADMIN_URL': 'adminUrl',
        'DEFAULT_NODE_COUNT': 'defaultNodeCount',
        'OPEN_USER_REG': 'openUserReg',
        'DEFAULT_REG_DAYS': 'defaultRegDays',
        'SMTP_HOST': 'smtpHost',
        'SMTP_PORT': 'smtpPort',
        'SMTP_USER': 'smtpUser',
        'SMTP_PASSWORD': 'smtpPassword',
        'SMTP_FROM': 'smtpFrom',
        'SMTP_FROM_NAME': 'smtpFromName',
        'SMTP_SSL': 'smtpSsl',
        'EMAIL_VERIFY_REG': 'emailVerifyReg',
        'TIANAPI_KEY': 'tianapiKey',
        'IP_API_SOURCE': 'ipApiSource',
    }
    # 构建反向映射：form字段名 -> config key
    form_to_config = {v: k for k, v in form_fields.items()}

    config_mapping = {}
    for key, value in request.form.items():
        config_key = key if key in form_fields else form_to_config.get(key)
        if config_key:
            config_mapping[config_key] = value

    return save_config_yaml(config_mapping)


@bp.route('/get_apikey' , methods=['POST'])
@login_required
@role_required("manager")
def get_apikey():
    with SqliteDB() as cursor:
        try:
            # 删除所有记录
            delete_query = "DELETE FROM api_keys;"
            cursor.execute(delete_query)
            num_rows_deleted = cursor.rowcount
            print(f"成功删除 {num_rows_deleted} 条记录")
        except Exception as e:
            print(f"删除记录时出现错误: {e}")
            return res('1', f"删除记录时出现错误: {e}", '')

    try:
        headscale_command = "headscale apikey create"
        result = subprocess.run(headscale_command, shell=True, capture_output=True, text=True, check=True)
        return res('0', '执行成功', result.stdout)
    except subprocess.CalledProcessError as e:
        return res('1', '执行失败', f"错误信息：{e.stderr}")



def _tail_lines(path, want, skip=0):
    """读日志末尾 want 行，跳过最新的 skip 行 —— 分页往回翻用。

    返回 (行列表, 是否还有更早的行)。

    headscale 的日志只增不删，原先 readlines() 是整读再切尾，文件一大光
    读就要卡很久。这里从末尾按档往回读（256KB 起，凑不够再翻四倍），绝
    大多数情况只碰最后一段。Health check / Monitoring log 是探活刷出来
    的噪声，顺手滤掉 —— 滤完不够行数就多读一段，不会因此少给。

    页码从 1 数起，第 1 页就是文件末尾那一段，往后翻看更早的。
    """
    noise = (b'Health check', b'Monitoring log')
    need = want + skip
    kept = []
    start = 0
    with open(path, 'rb') as f:
        size = f.seek(0, 2)               # 挪到末尾，返回值即文件大小
        for limit in (256 * 1024, 1024 * 1024, 4 * 1024 * 1024):
            start = max(0, size - limit)
            f.seek(start)
            # 按 \n 切分，每行都是完整的字节串（换行符不会落进多字节字符
            # 中间），所以单独解码某一行的中文不会切坏
            lines = f.read().split(b'\n')
            if start > 0:
                lines = lines[1:]         # 从中间切进去的，头一段是半行，丢掉
            kept = [l for l in lines if l and not any(n in l for n in noise)]
            if len(kept) >= need or start == 0 or limit == 4 * 1024 * 1024:
                break

    # 跳过末尾 skip 行，再往前取 want 行
    end = len(kept) - skip
    begin = max(0, end - want)
    page = kept[begin:max(0, end)]
    # begin > 0 是缓冲区里还有更早的行，start > 0 是文件更早的部分根本没
    # 读（撞上 4MB 上限）。两者都否就是翻到头了；这一页已经取空的话，也
    # 别再让前端继续往前翻 —— 否则翻过去只会是一片空白
    more = (begin > 0 or start > 0) and bool(page)
    return [l.decode('utf-8', 'replace') + '\n' for l in page], more


def _head_lines(path, want, skip=0):
    """从文件开头读 want 行，跳过最前面的 skip 行。

    翻到最早那段时用。最早的日志就在文件开头，只读前面一小段就够，不
    必碰后面几百 MB —— 和 _tail_lines 正好相反，两边各自负责近的那一端。

    返回 (行列表, 是否还有更晚的行)。
    """
    noise = (b'Health check', b'Monitoring log')
    kept = []
    with open(path, 'rb') as f:
        for raw in f:
            line = raw.rstrip(b'\n')
            if not line or any(n in line for n in noise):
                continue
            kept.append(line)
            if len(kept) > skip + want:   # 多留一行，用来判断后面还有没有
                break
    page = kept[skip:skip + want]
    more = len(kept) > skip + want
    return [l.decode('utf-8', 'replace') + '\n' for l in page], more


def _count_lines(path):
    """数日志的有效行数（滤掉探活噪声），用来算总页数。

    逐行 decode 再判断要好几秒（日志已经 480MB），所以按块读、用
    bytes.count 数行数和噪声出现次数 —— 两次都在 C 层完成，一秒上下
    就能扫完。噪声串正好跨块边界时会漏计一次、一行里同时出现两种噪声
    时会多计一次，两个误差都远小于一页，对页数没有影响。
    """
    noise = (b'Health check', b'Monitoring log')
    total = 0
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            total += chunk.count(b'\n')
            for n in noise:
                total -= chunk.count(n)
        # 末行没有换行符时，上面按 \n 数的那个循环漏掉了它
        size = f.seek(0, 2)
        if size:
            f.seek(size - 1)
            if f.read(1) != b'\n':
                total += 1
    return max(0, total)


@bp.route('/headscale_log', methods=['GET'])
@login_required
@role_required("manager")
def headscale_log():
    log_path = '/var/lib/headscale/headscale.log'
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(request.args.get('size', 100))
    except (TypeError, ValueError):
        size = 100
    page = max(1, page)
    size = min(max(size, 10), 500)        # 挡住手改参数，别一次拉爆
    try:
        # pos=head 从文件开头往后数（最早那端），默认从末尾往回数
        if request.args.get('pos') == 'head':
            lines, more = _head_lines(log_path, size, (page - 1) * size)
            has_older, has_newer = page > 1, more
        else:
            lines, more = _tail_lines(log_path, size, (page - 1) * size)
            has_older, has_newer = more, page > 1
        data = {
            'lines': ''.join(lines),
            'page': page,
            'size': size,
            'has_older': has_older,
            'has_newer': has_newer,
        }
        if request.args.get('total'):
            # 数总行数要把整个文件扫一遍（480MB 约一秒），所以只在弹窗打开
            # 时单独要一次，翻页不再重复算
            total = _count_lines(log_path)
            data['total_pages'] = max(1, (total + size - 1) // size)
        return res('0', 'ok', data)
    except FileNotFoundError:
        return res('1', '日志文件不存在', '')
    except Exception as e:
        return res('1', f'读取失败: {str(e)}', '')


@bp.route('/headscale_status', methods=['GET'])
@login_required
@role_required("manager")
def headscale_status():
    """健康检查：通过 HTTP 确认 headscale 是否真正在运行"""
    import requests
    try:
        r = requests.get('http://127.0.0.1:8080/health', timeout=2)
        return res('0', '运行中', {'running': r.status_code == 200})
    except Exception:
        return res('0', '已停止', {'running': False})


@bp.route('/switch_headscale', methods=['POST'])
@login_required
@role_required("manager")
def switch_headscale():
    status = request.form.get('Switch')
    if status == "true":
        result = start_headscale()
    else:
        result = stop_headscale()

    # 等待并验证实际状态
    import time, requests
    time.sleep(1.5)
    for _ in range(10):
        try:
            r = requests.get('http://127.0.0.1:8080/health', timeout=2)
            if (status == "true" and r.status_code == 200) or \
               (status == "false" and r.status_code != 200):
                return res('0', '操作成功', {})
        except Exception:
            if status == "false":
                return res('0', '操作成功', {})
        time.sleep(0.5)
    return res('1', '请检查端口占用或者查看详细日志', {})


@bp.route('/user_mode', methods=['POST'])
@login_required
@role_required("manager")
def user_mode():
    mode = request.form.get('mode', 'admin')
    session['user_mode'] = mode if mode in ('admin', 'user') else 'admin'
    return res('0', f'已切换到{"用户" if mode == "user" else "管理员"}模式', '')

