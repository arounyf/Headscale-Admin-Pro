
# 介绍
[![GitHub repo size](https://img.shields.io/github/repo-size/arounyf/Headscale-Admin-Pro)](https://github.com/arounyf/headscale-Admin)
[![Docker Image Size](https://img.shields.io/docker/image-size/runyf/hs-admin)](https://hub.docker.com/r/runyf/hs-admin)
[![docker pulls](https://img.shields.io/docker/pulls/runyf/hs-admin.svg?color=brightgreen)](https://hub.docker.com/r/runyf/hs-admin)
[![platfrom](https://img.shields.io/badge/platform-amd64%20%7C%20arm64-brightgreen)](https://hub.docker.com/r/runyf/hs-admin/tags)

重点升级：   
1、基于本人发布的headscale-Admin使用python进行了后端重构   
2、容器内置headscale、实现快速搭建   
3、容器内置流量监测、无需额外安装插件   
4、基于headscale新版本0.25.0进行开发和测试   

官方qq群： 892467054
# 时间线
2024年6月我接触到了tailscale,后在个人博客上发布了derper与headscale的搭建教程   
2024年9月8日headscale-Admin首个版本正式开源发布   
2025年3月26日Headscale-Admin-Pro正式开源发布   

# 使用docker部署
```shell
mkdir ~/hs-admin
cd ~/hs-admin
wget https://github.com/arounyf/Headscale-Admin-Pro/blob/main/docker-compose.yml
docker-compose up -d
```

1、修改配置文件1 ~/hs-admin/app/config.py


说明
- BEARER_TOKEN创建命令： `docker exec -it hs-admin  /app/headscale apikey create`
- TAILSCALE_UP_URL： headscale server url
- SERVER_NET：宿主机网卡名，流量统计使用
其它基本无需更改
   
1、修改配置文件2 ~/hs-admin/config/config.yaml   
   
此为headscale配置文件   


3、访问 http://ip:5000   
    
说明   

- 注册admin账户即为系统管理员账户   


# 功能
- 用户管理
- 用户自行注册
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


# 兼容性
hs-admin:v2.0基于headscale:v0.25.0开发测试

# 系统截图

![console](https://github.com/user-attachments/assets/6e25da2f-39f9-4217-b79e-344221c8f816)
![user](https://github.com/user-attachments/assets/1906c6ec-eb6f-44b1-af88-237ec16f1e99)
![reg](https://github.com/user-attachments/assets/59a43c57-682a-4cfd-83c0-8aa3d48a3d67)
![login](https://github.com/user-attachments/assets/e3d4029f-cc08-41e7-8dec-7cae4748a761)






