在原版基础上做了如下更改：
1.无需设置apikey自动设置
2.无需设置任何环境变量 headscale_up_url 自动从headscale配置文件config.yaml读取
3.实现双子域名如果登录后台的情况下自动添加节点，再也无需复制nodekey去后台添加
4.支持s6-overlay重构自动进程管理
5.改用alpine为底层容器，容器构建速度90s速度快，构建完成大约400M
6.同步手机号校验修改代码
启动之后需要修改headscale配置文件的server_url
caddy换成双子域名可体验网页自动添加 修改完成后执行重启 docker restart hs-admin

----------特别实现了ocid类似效果添加节点-----------------------------------------------------------------
 

# 使用docker部署
1. 安装
```shell
mkdir ~/hs-admin
cd ~/hs-admin
wget https://raw.githubusercontent.com/chenxudong2020/Headscale-Admin-Pro/refs/heads/urls/docker-compose.yml
docker-compose up -d
```

2. 修改配置文件 然后重启重启 
准备工作：主域名托管到cf 同时登录cf添加域名管理API key并复制保存 同时添加www 和 tailscale子域名并解析到VPS
然后对caddy的Caddy文件修改
``` {
    admin off
    auto_https disable_redirects
    servers {
        protocols h1 h2
    }
}

www.主域名:443 {
    tls {
		dns cloudflare CF域名管理key
	}
	encode gzip
    handle_path /.well-known/acme-challenge/* {
        file_server
    }

    reverse_proxy 127.0.0.1:5000 {
        transport http {
            versions h11 h2
        }
        header_up Host {host}
        header_up X-Real-IP {remote_addr}
        header_up X-Forwarded-For {remote_addr}
        header_up X-Forwarded-Proto {scheme}
    }
}

tailscale.主域名:443 {
     tls {
		dns cloudflare CF域名管理key
	}
	encode gzip

    handle_path /.well-known/acme-challenge/* {
        file_server
    }

    handle_path /admin* {
         redir https://www.dubu.host{uri} permanent
    }

    handle_path /register* {
        redir https://www.dubu.host/register{uri} permanent
    }

    reverse_proxy 127.0.0.1:8080 {
        transport http {
            versions h11 h2
        }
        header_up Host {host}
        header_up X-Real-IP {remote_addr}
        header_up X-Forwarded-For {remote_addr}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

修改headscale config.yaml server_url为 https://tailscale.主域名

3、访问 https://www.主域名
    
说明   

- 默认管理员admin 默认密码999888


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
headscale 0.25.0   
headscale 0.25.1   



# 系统截图

![console](https://github.com/user-attachments/assets/6e25da2f-39f9-4217-b79e-344221c8f816)
![user](https://github.com/user-attachments/assets/1906c6ec-eb6f-44b1-af88-237ec16f1e99)
![reg](https://github.com/user-attachments/assets/59a43c57-682a-4cfd-83c0-8aa3d48a3d67)
![login](https://github.com/user-attachments/assets/e3d4029f-cc08-41e7-8dec-7cae4748a761)






