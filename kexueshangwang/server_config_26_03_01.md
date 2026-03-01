# 服务器详细配置文档

> 📅 最后更新：2026年2月23日  
> 🖥️ 服务器：搬瓦工 CN2 GIA-E  
> 🌐 域名：qinfuqi.top  
> 👤 用户：echo  

---

## 目录

- [[#1. 服务器基本信息]]
- [[#2. 系统环境]]
- [[#3. V2Ray 配置]]
- [[#4. Nginx 配置]]
- [[#5. SSL 证书]]
- [[#6. Cloudflare CDN]]
- [[#7. Flask 网站]]
- [[#8. Python 环境]]
- [[#9. 客户端配置]]
- [[#10. 系统服务管理]]
- [[#11. 防火墙]]
- [[#12. 目录结构]]
- [[#13. 常用命令速查]]
- [[#14. 待办事项]]

---

## 1. 服务器基本信息

| 项目 | 内容 |
|------|------|
| 服务商 | 搬瓦工 BandwagonHost |
| 后台地址 | https://bwh81.net |
| 套餐 | CN2 GIA-E |
| 机房 | 洛杉矶 DC6 CN2 GIA |
| IP地址 | 67.230.164.20 |
| SSH端口 | 22 |
| SSH用户 | echo（sudo权限）|
| 操作系统 | Ubuntu 20.04.6 LTS |
| 内存 | 1GB |
| 硬盘 | 20GB |
| Swap | 2GB |

### SSH连接命令
```bash
ssh echo@67.230.164.20 -p 22
```

---

## 2. 系统环境

### 系统资源（优化后）
```
内存：1GB 总量，可用约700MB
硬盘：20GB 总量，已用约5.8GB
Swap：2GB
```

### 已清理的软件
```
microk8s   ← 释放约400MB内存
lxd        ← 释放硬盘空间
powershell ← 释放硬盘空间
core18     ← 释放硬盘空间
```

### 已安装的工具
```
curl, wget, vim, ufw, git
python3, python3-pip
unzip, build-essential
nginx, gunicorn
```

---

## 3. V2Ray 配置

### 重要说明
> `/api/v1/c8f3a2` 是一个**URL路径**，不是服务器上真实存在的文件夹。
> 当V2Ray客户端访问这个路径时，Nginx识别后将流量转发给V2Ray处理。

### 基本信息
| 项目 | 内容 |
|------|------|
| 版本 | V2Ray 5.12.1 |
| 协议 | VMess |
| 传输方式 | WebSocket |
| 监听地址 | 127.0.0.1（仅本地，不对外暴露）|
| 监听端口 | 10000 |
| WebSocket路径（URL）| /api/v1/c8f3a2 |
| UUID | b8e46a10-5287-4b20-a916-0781cd71a60e |
| TLS | 由Nginx处理 |

### 安装方式
手动下载安装（官方脚本在此服务器上失败）：
```bash
cd ~
wget https://github.com/v2fly/v2ray-core/releases/download/v5.12.1/v2ray-linux-64.zip
unzip v2ray-linux-64.zip -d v2ray-tmp
sudo cp v2ray-tmp/v2ray /usr/local/bin/
sudo chmod +x /usr/local/bin/v2ray
sudo mkdir -p /usr/local/share/v2ray
sudo cp v2ray-tmp/geoip.dat /usr/local/share/v2ray/
sudo cp v2ray-tmp/geosite.dat /usr/local/share/v2ray/
```

### 文件位置
```
主程序：    /usr/local/bin/v2ray
配置文件：  /usr/local/etc/v2ray/config.json
GeoIP：    /usr/local/share/v2ray/geoip.dat
GeoSite：  /usr/local/share/v2ray/geosite.dat
系统服务：  /etc/systemd/system/v2ray.service
```

### 配置文件内容
`/usr/local/etc/v2ray/config.json`：
```json
{
  "inbounds": [{
    "port": 10000,
    "listen": "127.0.0.1",
    "protocol": "vmess",
    "settings": {
      "clients": [{
        "id": "b8e46a10-5287-4b20-a916-0781cd71a60e",
        "alterId": 0
      }]
    },
    "streamSettings": {
      "network": "ws",
      "wsSettings": {
        "path": "/api/v1/c8f3a2"
      }
    }
  }],
  "outbounds": [{
    "protocol": "freedom"
  }]
}
```

### 系统服务文件
`/etc/systemd/system/v2ray.service`：
```ini
[Unit]
Description=V2Ray Service
After=network.target

[Service]
User=nobody
ExecStart=/usr/local/bin/v2ray run -config /usr/local/etc/v2ray/config.json
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

---

## 4. Nginx 配置

### 基本信息
| 项目 | 内容 |
|------|------|
| 版本 | nginx/1.18.0 |
| 监听端口 | 80（重定向到443），443（HTTPS）|
| 配置文件 | /etc/nginx/sites-available/default |
| 访问日志 | /var/log/nginx/access.log |
| 错误日志 | /var/log/nginx/error.log |

### 流量路由规则
```
http://qinfuqi.top/*               → 301重定向到HTTPS
https://qinfuqi.top/*              → Flask应用（127.0.0.1:5000）
https://qinfuqi.top/api/v1/c8f3a2 → V2Ray（127.0.0.1:10000）
```

### 配置文件内容
`/etc/nginx/sites-available/default`：
```nginx
server {
    listen 80;
    server_name qinfuqi.top www.qinfuqi.top;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name qinfuqi.top www.qinfuqi.top;

    ssl_certificate     /etc/nginx/ssl/qinfuqi.top.pem;
    ssl_certificate_key /etc/nginx/ssl/qinfuqi.top.key;

    # 转发到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # V2Ray流量转发（URL路径，非文件系统路径）
    location /api/v1/c8f3a2 {
        proxy_pass http://127.0.0.1:10000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 5. SSL 证书

### 证书信息
| 项目 | 内容 |
|------|------|
| 类型 | Cloudflare Origin Certificate |
| 证书文件 | /etc/nginx/ssl/qinfuqi.top.pem |
| 私钥文件 | /etc/nginx/ssl/qinfuqi.top.key |
| 申请位置 | Cloudflare → SSL/TLS → Origin Server |
| SSL模式 | Full |

### 加密链路
```
用户 ←HTTPS→ Cloudflare ←HTTPS→ Nginx（使用Cloudflare源证书）
```

> ⚠️ **重要**：
> - 证书文件内容以 `-----BEGIN CERTIFICATE-----` 开头
> - 私钥文件内容以 `-----BEGIN PRIVATE KEY-----` 开头
> - 私钥只在创建时显示一次，务必妥善备份！

---

## 6. Cloudflare CDN

### 域名信息
| 项目 | 内容 |
|------|------|
| 域名注册商 | Namesilo |
| 域名 | qinfuqi.top |
| CDN服务 | Cloudflare 免费版 |
| 自动续费 | 已关闭 |

### NS记录（在Namesilo设置）
```
olof.ns.cloudflare.com
susan.ns.cloudflare.com
```

### DNS记录（在Cloudflare设置）
| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|---------|
| A | qinfuqi.top | 67.230.164.20 | 🟠 Proxied（橙色云朵）|
| A | www | 67.230.164.20 | 🟠 Proxied（橙色云朵）|

### 关键设置
```
SSL/TLS模式：Full
WebSockets：已开启（Network选项卡）
```

### 验证CDN是否工作
```bash
# 服务器日志里看到Cloudflare IP段说明CDN正常
sudo tail -f /var/log/nginx/access.log

# Cloudflare的IP段：
# 104.16.0.0/12   如：104.23.251.140
# 172.64.0.0/13   如：172.64.217.14
# 162.158.0.0/15  如：162.158.187.142
```

---

## 7. Flask 网站

### 基本信息
| 项目 | 内容 |
|------|------|
| 框架 | Flask |
| 网站目录 | /home/echo/blog |
| 主程序 | /home/echo/blog/app.py |
| 虚拟环境 | /home/echo/blog/venv |
| 监听地址 | 127.0.0.1:5000 |
| WSGI服务器 | Gunicorn 25.1.0 |
| Worker数量 | 2 |

### 系统服务文件
`/etc/systemd/system/blog.service`：
```ini
[Unit]
Description=Flask Blog Service
After=network.target

[Service]
User=echo
WorkingDirectory=/home/echo/blog
Environment="PATH=/home/echo/blog/venv/bin"
ExecStart=/home/echo/blog/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 本地测试
```bash
curl http://127.0.0.1:5000
```

---

## 8. Python 环境

### Python版本
```
Python 3.11.8（从源码编译安装）
安装位置：/usr/local/bin/python3.11
```

### 为什么从源码编译
```
Ubuntu 20.04 官方仓库只有 Python 3.8
deadsnakes PPA 在此服务器上无法正常工作
因此从 Python 官网下载源码手动编译安装
```

### 编译安装步骤（备忘）
```bash
sudo apt install -y build-essential zlib1g-dev libncurses5-dev \
libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev \
libsqlite3-dev wget

cd /tmp
wget https://www.python.org/ftp/python/3.11.8/Python-3.11.8.tgz
tar -xf Python-3.11.8.tgz
cd Python-3.11.8
./configure --enable-optimizations
make -j2
sudo make altinstall
```

### AI自动化环境（待完成）
```bash
mkdir -p ~/ai-coder
cd ~/ai-coder
python3.11 -m venv venv
source venv/bin/activate
pip install anthropic openai python-dotenv requests
```

`~/ai-coder/.env` 文件（待填写）：
```
ANTHROPIC_API_KEY=你的Claude API Key
OPENAI_API_KEY=你的OpenAI API Key
```

---

## 9. 客户端配置

### 通用连接参数
| 字段 | 值 |
|------|-----|
| 地址 | qinfuqi.top |
| 端口 | 443 |
| 用户ID（UUID）| b8e46a10-5287-4b20-a916-0781cd71a60e |
| 额外ID（alterId）| 0 |
| 加密方式 | auto |
| 传输协议 | WebSocket (ws) |
| 路径（URL路径）| /api/v1/c8f3a2 |
| TLS | 开启 |

### Windows客户端（v2rayN）
```
下载：https://github.com/2dust/v2rayN/releases/latest
文件：v2rayN-With-Core.zip
启动代理：右键任务栏图标 → 系统代理 → 自动配置系统代理
```

### Android客户端（v2rayNG）
```
下载：https://github.com/2dust/v2rayNG/releases/latest
文件：v2rayNG_x.x.x_arm64-v8a.apk（现代手机选arm64）
导入：扫描v2rayN生成的二维码（最简单）
```

---

## 10. 系统服务管理

### 三个核心服务
| 服务 | 作用 | 服务文件 |
|------|------|---------|
| v2ray | V2Ray翻墙代理 | /etc/systemd/system/v2ray.service |
| nginx | 反向代理+SSL | /lib/systemd/system/nginx.service |
| blog | Flask网站 | /etc/systemd/system/blog.service |

### 常用操作
```bash
# 查看所有服务状态
sudo systemctl status v2ray nginx blog

# 重启服务
sudo systemctl restart v2ray
sudo systemctl reload nginx      # 重新加载配置（不中断连接）
sudo systemctl restart blog

# 开机自启（已配置）
sudo systemctl enable v2ray
sudo systemctl enable nginx
sudo systemctl enable blog
```

---

## 11. 防火墙

### 当前规则
| 端口 | 用途 | 状态 |
|------|------|------|
| 22 | SSH | 开放 |
| 80 | HTTP | 开放 |
| 443 | HTTPS | 开放 |

```bash
sudo ufw status                       # 查看状态
sudo ufw allow 端口号                 # 开放端口
sudo ufw delete allow 端口号          # 关闭端口
```

> ⚠️ 修改防火墙前必须先确认SSH端口已放行，否则会把自己锁在外面！

---

## 12. 目录结构

```
/
├── usr/local/
│   ├── bin/
│   │   └── v2ray                        ← V2Ray主程序
│   ├── etc/
│   │   └── v2ray/
│   │       └── config.json              ← V2Ray配置文件
│   └── share/
│       └── v2ray/
│           ├── geoip.dat                ← IP地理位置数据库
│           └── geosite.dat              ← 网站分类数据库
├── etc/
│   ├── nginx/
│   │   ├── sites-available/
│   │   │   └── default                  ← Nginx配置文件
│   │   └── ssl/
│   │       ├── qinfuqi.top.pem          ← SSL证书
│   │       └── qinfuqi.top.key          ← SSL私钥（保密！）
│   └── systemd/system/
│       ├── v2ray.service                ← V2Ray系统服务
│       └── blog.service                 ← Flask系统服务
├── var/
│   ├── www/html/                        ← 静态网站目录（已不使用）
│   └── log/nginx/
│       ├── access.log                   ← 访问日志
│       └── error.log                    ← 错误日志
└── home/echo/
    ├── blog/                            ← Flask网站目录
    │   ├── app.py                       ← Flask主程序
    │   └── venv/                        ← Python虚拟环境
    ├── v2ray-tmp/                       ← V2Ray安装包（可删除）
    └── ai-coder/                        ← AI自动化目录（待配置）
        ├── venv/
        └── .env                         ← API Key配置文件
```

---

## 13. 常用命令速查

### 系统状态
```bash
free -h                                  # 内存使用情况
df -h                                    # 硬盘使用情况
ps aux | grep gunicorn                   # 查看Gunicorn进程
```

### 日志查看
```bash
sudo tail -f /var/log/nginx/access.log   # 实时访问日志
sudo tail -f /var/log/nginx/error.log    # 实时错误日志
```

### 测试服务
```bash
curl http://127.0.0.1:5000               # 本地测试Flask
curl -I https://qinfuqi.top              # 测试HTTPS
sudo nginx -t                            # 检查Nginx配置语法
```

### Flask虚拟环境
```bash
cd /home/echo/blog && source venv/bin/activate
```

### 清除Cloudflare缓存
```
Cloudflare后台 → Caching → Configuration → Purge Everything
```

---

## 14. 待办事项

- [ ] 申请Claude API Key（https://console.anthropic.com）
- [ ] 申请OpenAI API Key（https://platform.openai.com）
- [ ] 配置 ~/ai-coder/.env 文件
- [ ] 编写AI自动生成代码脚本
- [ ] 测试AI自动化流程
- [ ] 考虑将VMess协议升级为VLESS（更轻量，特征更少）
- [ ] 定期备份UUID和SSL证书私钥到安全位置

---

## 附录：整体架构图

```
┌─────────────────────────────────────────┐
│             用户设备                     │
│  Windows(v2rayN) / Android(v2rayNG)     │
└──────────────────┬──────────────────────┘
                   │ HTTPS 443端口
                   ▼
┌─────────────────────────────────────────┐
│           Cloudflare CDN                │
│  · 隐藏服务器真实IP                     │
│  · SSL/TLS加密                          │
│  · 缓存加速                             │
│  NS: olof/susan .ns.cloudflare.com      │
└──────────────────┬──────────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────────┐
│      搬瓦工服务器 67.230.164.20          │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │       Nginx (443端口)            │   │
│  │  SSL证书：qinfuqi.top.pem/key    │   │
│  └────────┬─────────────┬───────────┘   │
│           │             │               │
│    URL: / │             │ URL:          │
│           │             │ /api/v1/      │
│           │             │ c8f3a2        │
│           ▼             ▼               │
│  ┌─────────────┐  ┌──────────────┐     │
│  │ Flask网站   │  │   V2Ray      │     │
│  │ :5000       │  │   :10000     │     │
│  │ /home/echo  │  │ VMess+WS     │     │
│  │ /blog       │  │              │     │
│  └─────────────┘  └──────┬───────┘     │
└─────────────────────────┼──────────────┘
                           │
                           ▼
                     自由访问互联网 🌐
```
