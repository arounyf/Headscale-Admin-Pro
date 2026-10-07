
# 介绍
[![GitHub repo size](https://img.shields.io/github/repo-size/arounyf/Headscale-Admin-Pro)](https://github.com/arounyf/headscale-Admin)
[![Docker Image Size](https://img.shields.io/docker/image-size/runyf/hs-admin)](https://hub.docker.com/r/runyf/hs-admin)
[![docker pulls](https://img.shields.io/docker/pulls/runyf/hs-admin.svg?color=brightgreen)](https://hub.docker.com/r/runyf/hs-admin)
[![platform](https://img.shields.io/badge/platform-linux%2Famd64-brightgreen)](https://hub.docker.com/r/runyf/hs-admin/tags)

重点升级：   
1、基于本人发布的headscale-Admin使用python进行了后端重构   
2、容器内置headscale、实现快速搭建   
3、容器内置流量监测、无需额外安装插件   
4、基于headscale最新新版本进行开发和测试   

官方qq群： 892467054
# 时间线
2024年6月开始接触 headscale   
2024年9月8日 headscale-Admin 首个版本正式发布   
2025年3月26日 Headscale-Admin-Pro 基于python重构新版本正式发布  


# 使用docker部署
```shell
mkdir ~/hs-admin
cd ~/hs-admin
wget https://raw.githubusercontent.com/arounyf/Headscale-Admin-Pro/refs/heads/main/docker-compose.yml
docker-compose up -d
```

   
1、访问 http://ip:5000，注册admin账户即为系统管理员账户   

2、进入后台设置，修改 **server url**、网卡名等，修改之后点击保存，最后重启headscale

   server url 是**客户端连接 headscale 的地址**，要填客户端访问得到的地址，例如
   `http://192.168.1.10:8080`（局域网直连）或 `https://hs.example.com`（配好反向代理后）。
   出厂值 `http://<你的域名>:8080` 只是占位符：**不改的话，「指令」页给出的第一条命令
   `tailscale up --login-server=...` 会在客户端上解析失败**（报的是域名解析不了，
   不会指向这个设置项，容易卡在这一步）。

   它就是配置文件 `~/hs-admin/config/config.yaml` 里的 `server_url`，在设置页保存时会重写该文件。

3、配置derp中转服务器（headscale配置文件路径 ~/hs-admin/config/config.yaml）

4、配置nginx，配置示例 nginx-example.conf(可选)



# 功能
- 用户管理
- 用户独立后台
- 用户到期管理
- 流量统计
- 基于用户ACL
- 节点管理
- 路由管理
- 日志管理
- 预认证密钥管理
- 角色管理
- api和menu权限管理
- 内置headscale
- 内置配置在线修改
- 一键添加节点(需配置反向代理)
- 自动更新apikey


# 版本关系

> 注意 hs 代表非官方原版 headscale，因数据库适配问题不得不对 headscale 代码进行修改。从 v3.0 开始支持从上一个版本升级，操作之前请一定要备份好你的数据。

| Headscale-Admin-Pro | 内置的 headscale |
| --- | --- |
| v3.x | v0.27.x-hs |
| v4.x | v0.28.x-hs |
| v5.0 – v5.4 | v0.29.x-hs |
| v5.4.1 起 | 与面板同一个 commit，版本号继承上游 CHANGELOG |

v5.4 及以前，headscale 二进制是从 `arounyf/headscale` 的一个 release 里下载的，上表
右边就是那个被固定在 `Dockerfile` 里的版本。这条链路有个隐患：**面板代码和二进制之间
没有任何机制保证对齐** —— 改了 proto 却忘了改那个下载 URL，用户点注册时就会撞上
`unknown field`，而报错来自 protojson 的解析，完全看不出是版本没对上。

v5.4.1 起 headscale 源码以 `git subtree` 并入本仓库的 [`headscale/`](headscale/) 目录，
二进制由 `Dockerfile` 从这棵树直接构建，两者永远出自同一个 commit。**版本号继承上游**：
构建时从 `headscale/CHANGELOG.md` 顶部取上游最新一次发布的 `x.y.z`，缀上 `-hs`
打进二进制，`git subtree pull` 之后自动就是对的，没有需要手工维护的数字，面板「关于」
里那一行显示的就是它（例如 `headscale v0.29.4-hs`）。每个 Release 也会附上这个二进制
本身（`releases/download/<tag>/headscale`，linux/amd64），和镜像里跑的是同一个构建。
上游怎么同步、改 headscale 代码时要注意什么，见
[`headscale/MERGING-UPSTREAM.md`](headscale/MERGING-UPSTREAM.md)。

# 如何升级

> **升级前务必备份数据！** 请勿跨 headscale 版本升级，在 [Release](https://github.com/arounyf/Headscale-Admin-Pro/releases) 中可查看当前版本详细升级说明。





# 系统截图
<img width="1280" alt="控制台" src="docs/screenshots/console.png" />
<img width="1280" alt="用户管理" src="docs/screenshots/user.png" />
<img width="1280" alt="节点管理" src="docs/screenshots/node.png" />
<img width="1280" alt="路由管理" src="docs/screenshots/route.png" />
<img width="1280" alt="ACL 策略" src="docs/screenshots/acl.png" />
<img width="1280" alt="预认证密钥" src="docs/screenshots/preauthkey.png" />
<img width="1280" alt="指令" src="docs/screenshots/deploy.png" />
<img width="1280" alt="日志" src="docs/screenshots/log.png" />
<img width="1280" alt="登录页" src="docs/screenshots/login.png" />
<img width="1280" alt="注册页" src="docs/screenshots/register.png" />





