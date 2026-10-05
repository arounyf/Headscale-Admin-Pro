import json
import os
import subprocess
import tempfile
from flask_login import login_required, current_user
from login_setup import role_required
from flask import Blueprint, request
from utils import reload_headscale, res

bp = Blueprint("acl", __name__, url_prefix='/api/acl')

ACL_PATH = "/etc/headscale/acl.hujson"

# 容器里的 headscale CLI，init.sh 启动时从 /app 复制到 /usr/bin。
HEADSCALE_BIN = "headscale"


def _run_headscale(args, timeout=30):
    """跑 headscale CLI，返回 (returncode, stdout, stderr)。"""
    try:
        p = subprocess.run([HEADSCALE_BIN] + args,
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, '', f'找不到 {HEADSCALE_BIN} 命令'
    except subprocess.TimeoutExpired:
        return 124, '', f'{HEADSCALE_BIN} 命令超时'


def _headscale_error(text):
    """把 CLI 的报错剥到 headscale 自己那句话。

    cobra 包一层 "Error: "，gRPC 再包一层 "rpc error: code = Unknown desc = "，
    剥掉这两层剩下的形如
    "setting policy: parsing policy: parsing HuJSON: hujson: line 2, column 1: ..."，
    行号列号还在里面，前端据此跳到出错行。
    """
    msg = (text or '').strip()
    if not msg:
        return 'headscale 执行失败，且没有任何输出'

    if ' desc = ' in msg:
        msg = msg.split(' desc = ', 1)[1]
    elif msg.startswith('Error: '):
        msg = msg[len('Error: '):]

    return msg

# ACL 文件读不到时的兜底内容，必须和 init.sh 写下的出厂 acl.hujson 一致。
# 这里曾经是另一份（没有 group:admin，且把 autogroup:internet 开给
# autogroup:member），管理员看到兜底内容后随手一存，出口就等于对所有用户
# 开放了 —— 和出厂默认的「仅管理员」正好相反。
DEFAULT_ACL = {
    "randomizeClientPort": True,
    "groups": {
        "group:admin": ["admin@"],
    },
    "acls": [
        {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]},
        {"action": "accept", "src": ["group:admin"], "dst": ["autogroup:internet:*"]},
    ],
}


@bp.route('/get_acl', methods=['GET', 'POST'])
@login_required
@role_required("manager")
def get_acl():
    """读取当前 ACL 文件，原样返回文件文本。

    以前是 json.load 再 json.dumps，等于把文件按 Python 的排版重排一遍：
    编辑器里排好的 ["autogroup:member"] 这种紧凑数组，一刷新就被摊成一行一个
    元素。现在直接把磁盘上的字节交出去，看到的永远和文件一致。

    文件不存在时给一份默认模板当起点；读失败（权限、编码）就给空串，让前端
    提示"ACL 文件为空"，不要把异常吞成一份看起来正常的默认 ACL —— 那样用户
    会以为这就是当前策略，一保存就把真文件覆盖了。
    """
    try:
        with open(ACL_PATH, 'r') as f:
            return res('0', '', f.read())
    except FileNotFoundError:
        return res('0', '', json.dumps(DEFAULT_ACL, indent=4, ensure_ascii=False))
    except OSError:
        return res('0', '', '')


@bp.route('/save_acl', methods=['POST'])
@login_required
@role_required("manager")
def save_acl():
    """把 ACL 交给 headscale 校验并落盘。

    以前是这里 json.loads 校验、open(ACL_PATH,'w') 写文件、再 kill -HUP，两个后果：
    一是比 headscale 自己还严 —— 注释、尾逗号都是合法 HuJSON，却被 json.loads 拒掉；
    二是坏策略已经写进文件、重载失败又只打成日志，headscale 下次重启会直接起不来
    （而面板的 start_headscale 只在面板启动时调一次，不会自动拉起）。

    现在文件由 headscale 自己写（policy.mode: file 时落 policy.path，database 时落库）：
    它先解析策略、跑 tests/sshTests，通过了才原子替换文件，校验不过磁盘一个字节都不动。
    本函数只负责把内容搬进一个临时文件、把 headscale 的原话搬回给前端。
    """
    raw = request.form.get('acl', '')

    if not raw.strip():
        return res('1', 'ACL 内容为空')

    fd, tmp_path = tempfile.mkstemp(prefix='acl-', suffix='.hujson')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(raw)

        code, out, err = _run_headscale(['policy', 'set', '-f', tmp_path])
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if code != 0:
        return res('1', _headscale_error(err or out))

    # 这里不再发 SIGHUP：headscale 写完就重新加载并分发给所有节点了。
    return res('0', '保存成功，headscale 已生效')


@bp.route('/reload', methods=['POST'])
@login_required
@role_required("manager")
def reload():
    return reload_headscale()
