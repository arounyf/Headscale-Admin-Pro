
# 介绍
[![GitHub repo size](https://img.shields.io/github/repo-size/arounyf/Headscale-Admin-Pro)](https://github.com/arounyf/headscale-Admin)
[![Docker Image Size](https://img.shields.io/docker/image-size/runyf/hs-admin)](https://hub.docker.com/r/runyf/hs-admin)
[![docker pulls](https://img.shields.io/docker/pulls/runyf/hs-admin.svg?color=brightgreen)](https://hub.docker.com/r/runyf/hs-admin)
[![platfrom](https://img.shields.io/badge/platform-amd64%20%7C%20arm64-brightgreen)](https://hub.docker.com/r/runyf/hs-admin/tags)

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

2、进入后台设置网卡名、并确认其它配置是否需要修改，修改之后重启headscale

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
 注意 runyf代表非官方原版headscale，因数据库适配问题不得不对headscale代码进行修改
| Headscale-Admin-Pro | headscale |
| --- | --- |
| v2.7 | v0.25.1 |
| v2.8 | v0.26.1 |
| v3.0 | v0.27.1-runyf |



# 系统截图
<img width="1280" alt="runyf_20250506230722" src="https://github.com/user-attachments/assets/d4c35e9e-d17a-46be-886d-50dd5a2425e9" />
<img width="1280" alt="runyf_20250506230832" src="https://github.com/user-attachments/assets/f30d6a9f-6042-46c0-825a-d4bffdb02b68" />
<img width="1280" alt="runyf_20250506230908" src="https://github.com/user-attachments/assets/78699c3d-6e54-4fcd-a6f4-889e77f17819" />
<img width="1280" alt="runyf_20250506231108" src="https://github.com/user-attachments/assets/41dde683-b95b-4fda-8396-a684f8de6f10" />
<img width="1280" alt="runyf_20250506230937" src="https://github.com/user-attachments/assets/bd234e91-a4fc-4299-b291-22235ba9bed9" />
<img width="1280" alt="runyf_20250506230957" src="https://github.com/user-attachments/assets/a1069cb4-e233-4220-aa54-6c0f2bab4e5e" />





