#!/bin/bash


# 接收传递进来的参数
start_command="$1"

# 定义宿主机挂载目录和容器内目标目录
INIT_DATA_APP_DIR="/init_data"
CONTAINER_CONFIG_DIR="/etc/headscale"
CONTAINER_DB_DIR="/var/lib/headscale"
CONTAINER_APP_DIR="/app"


mkdir /app
mkdir /etc/headscale
mkdir /var/lib/headscale

cd /app


# 检查容器内的 headscale 目录是否为空
if [ -z "$(ls -A $CONTAINER_CONFIG_DIR 2>/dev/null)" ]; then
    cp -r $INIT_DATA_APP_DIR/config.yaml $CONTAINER_CONFIG_DIR
    cp -r $INIT_DATA_APP_DIR/derp.yaml $CONTAINER_CONFIG_DIR
	echo "复制headscale配置文件"
	touch $CONTAINER_CONFIG_DIR/acl.hujson
	echo "创建ACL文件"
else
    echo "检测到headscale存在配置文件"
fi


# 检查容器内的 app 目录是否为空
if [ -z "$(ls -A $CONTAINER_APP_DIR 2>/dev/null)" ]; then
	echo "复制flask-app文件"
  cp -r $INIT_DATA_APP_DIR/* $CONTAINER_APP_DIR
	rm $CONTAINER_APP_DIR/config.yaml
	rm $CONTAINER_APP_DIR/derp.yaml
	rm $CONTAINER_APP_DIR/init.sh
	rm $CONTAINER_APP_DIR/Dockerfile
	rm $CONTAINER_APP_DIR/README.md
	rm $CONTAINER_APP_DIR/docker-compose.yml
	rm $CONTAINER_APP_DIR/nginx-example.conf
	rm $CONTAINER_APP_DIR/data.json
else
    echo "检测到flask-app存在已有数据"
fi

# 检查容器内的 DB存放 目录是否为空
if [ -z "$(ls -A $CONTAINER_DB_DIR 2>/dev/null)" ]; then
	echo "将自动生成流量统计文件"
	cp -r $INIT_DATA_APP_DIR/data.json $CONTAINER_DB_DIR
else
    echo "检测到data已有数据"
fi


cp headscale /usr/bin
chmod u+x /usr/bin/headscale

# 执行传递进来的启动命令
eval $start_command
