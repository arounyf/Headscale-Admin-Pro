FROM ubuntu:22.04

# 创建一个工作目录
WORKDIR /init_data

# 将当前目录下的内容复制到工作目录中
COPY . /init_data
RUN ls | grep sh && sleep 3
RUN chmod u+x init.sh


# 写入国内软件源配置信息到 sources.list 文件
RUN echo "# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to\n# newer versions of the distribution.\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy main restricted\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy main restricted\n\n## Major bug fix updates produced after the final release of the\n## distribution.\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy-updates main restricted\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy-updates main restricted\n\n## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu\n## team. Also, please note that software in universe WILL NOT receive any\n## review or updates from the Ubuntu security team.\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy universe\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy universe\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy-updates universe\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy-updates universe\n\n## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu\n## team, and may not be under a free licence. Please satisfy yourself as to\n## your rights to use the software. Also, please note that software in\n## multiverse WILL NOT receive any review or updates from the Ubuntu\n## security team.\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy multiverse\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy multiverse\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy-updates multiverse\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy-updates multiverse\n\n## N.B. software from this repository may not have been tested as\n## extensively as that contained in the main release, although it includes\n## newer versions of some applications which may provide useful features.\n## Also, please note that software in backports WILL NOT receive any review\n## or updates from the Ubuntu security team.\ndeb http://cn.archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse\n# deb-src http://cn.archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse\ndeb http://security.ubuntu.com/ubuntu/ jammy-security main restricted\n# deb-src http://security.ubuntu.com/ubuntu/ jammy-security main restricted\ndeb http://security.ubuntu.com/ubuntu/ jammy-security universe\n# deb-src http://security.ubuntu.com/ubuntu/ jammy-security universe\ndeb http://security.ubuntu.com/ubuntu/ jammy-security multiverse\n# deb-src http://security.ubuntu.com/ubuntu/ jammy-security multiverse\n" > /etc/apt/sources.list


# 更新包管理器并安装必要的工具
RUN apt-get update 
RUN apt-get install tzdata
RUN apt-get install net-tools -y
RUN apt-get install iputils-ping -y
RUN apt-get install python3 -y
RUN apt-get install pip -y
RUN apt-get install wget -y


# 安装flask
RUN pip3 install flask
RUN pip3 install sqlalchemy
RUN pip3 install flask_sqlalchemy
RUN pip3 install wtforms
RUN pip3 install captcha
RUN pip3 install flask_migrate
RUN pip3 install psutil
RUN pip3 install flask_login
RUN pip3 install requests
RUN pip3 install apscheduler

# 下载headscale

RUN wget -O headscale https://github.com/juanfont/headscale/releases/download/v0.25.1/headscale_0.25.1_linux_amd64


CMD ["sh", "-c", "./init.sh './headscale serve & python3 app.py'"]