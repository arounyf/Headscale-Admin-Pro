#!/bin/bash
set -e

# ==========================================
# headscale v0.29.0-runyf 部署/升级脚本
# ==========================================

BRANCH="v0.29.0-runyf"
REPO="https://github.com/arounyf/headscale.git"
GO_VERSION="1.26.4"
BUILD_DIR="/tmp/headscale-build"
DB_PATH="/var/lib/headscale/db.sqlite"
BIN_PATH="/usr/local/bin/headscale"

echo ">>> [1/5] 检查 Go $GO_VERSION"
if ! command -v go &>/dev/null || ! go version | grep -q "$GO_VERSION"; then
    echo "安装 Go $GO_VERSION ..."
    wget -q "https://dl.google.com/go/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
    tar -C /usr/local -xzf /tmp/go.tar.gz
    echo 'export PATH=$PATH:/usr/local/go/bin' > /etc/profile.d/go.sh
    source /etc/profile.d/go.sh
    rm /tmp/go.tar.gz
fi
go version

echo ">>> [2/5] 编译 headscale ($BRANCH)"
rm -rf "$BUILD_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$BUILD_DIR"
cd "$BUILD_DIR"
go build -v -o headscale ./cmd/headscale

echo ">>> [3/5] 备份数据库"
systemctl stop headscale 2>/dev/null || true
if [ -f "$DB_PATH" ]; then
    BACKUP="${DB_PATH}.bak.$(date +%Y%m%d-%H%M%S)"
    cp "$DB_PATH" "$BACKUP"
    echo "备份完成: $BACKUP"
else
    echo "无现有数据库，跳过备份"
fi

echo ">>> [4/5] 安装二进制"
mv headscale "$BIN_PATH"
chmod u+x "$BIN_PATH"
"$BIN_PATH" version

echo ">>> [5/5] 启动并验证"
systemctl start headscale
sleep 2
systemctl status headscale --no-pager | head -10

echo ""
echo "========================================"
echo "部署完成。日志: journalctl -u headscale -f"
echo "回滚方法: cp $BACKUP $DB_PATH && systemctl restart headscale"
echo "========================================"
