# V2Ray 完整配置文档

> 📅 最后更新：2026年3月1日
> 🌐 域名：qinfuqi.top
> 🖥️ 服务器：搬瓦工 CN2 GIA-E 洛杉矶

---

## 目录

- [[#1. 整体架构]]
- [[#2. 服务器端配置]]
- [[#3. 客户端配置]]
- [[#4. Cloudflare CDN配置]]
- [[#5. 优选IP配置]]
- [[#6. 性能指标]]
- [[#7. 工作原理详解]]
- [[#8. 常见问题]]
- [[#9. 定期维护]]

---

## 1. 整体架构

### 完整链路图

```
┌─────────────────────────────────────────────────┐
│                  你的电脑                         │
│           v2rayN客户端                            │
│    地址：198.41.203.72（Cloudflare优选IP）        │
│    SNI：qinfuqi.top                              │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS 443端口
                   │ VLESS + WebSocket + TLS
                   ▼
┌─────────────────────────────────────────────────┐
│           Cloudflare CDN                         │
│    优选节点：198.41.203.72                        │
│    位置：洛杉矶 LAX                               │
│    作用：隐藏真实IP / 加速 / 防封锁               │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────────────────┐
│         搬瓦工服务器 67.230.164.20               │
│         CN2 GIA 洛杉矶机房                        │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │           Nginx（443端口）                 │  │
│  │   SSL证书：Cloudflare Origin Certificate  │  │
│  └────────────────┬──────────────────────────┘  │
│                   │ 识别路径 /api/v1/c8f3a2      │
│                   ▼                              │
│  ┌───────────────────────────────────────────┐  │
│  │         V2Ray（127.0.0.1:10000）           │  │
│  │         协议：VLESS                        │  │
│  │         传输：WebSocket                    │  │
│  └────────────────┬──────────────────────────┘  │
└───────────────────┼──────────────────────────────┘
                    │
                    ▼
              自由访问互联网 🌐
```

### 各组件职责

| 组件 | 职责 |
|------|------|
| v2rayN客户端 | 加密流量，伪装成正常HTTPS请求 |
| Cloudflare CDN | 隐藏服务器真实IP，防止被封锁 |
| Nginx | SSL终止，根据路径分发流量 |
| V2Ray服务端 | 解密流量，转发到目标网站 |

---

## 2. 服务器端配置

### 基本信息

| 项目 | 内容 |
|------|------|
| 服务器IP | 67.230.164.20 |
| 域名 | qinfuqi.top |
| 系统 | AlmaLinux 9 |
| 机房 | 洛杉矶 CN2 GIA |
| V2Ray版本 | 5.12.1 |

### V2Ray配置文件

路径：`/usr/local/etc/v2ray/config.json`

```json
{
  "inbounds": [{
    "port": 10000,
    "listen": "127.0.0.1",
    "protocol": "vless",
    "settings": {
      "clients": [{
        "id": "b8e46a10-5287-4b20-a916-0781cd71a60e",
        "flow": ""
      }],
      "decryption": "none"
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

### 配置说明

| 字段 | 值 | 说明 |
|------|-----|------|
| port | 10000 | V2Ray监听端口，仅本地访问 |
| listen | 127.0.0.1 | 只监听本地，不对外暴露 |
| protocol | vless | 使用VLESS协议（比VMess更轻量）|
| id | b8e46a10-... | UUID，客户端身份验证 |
| decryption | none | VLESS不需要加密（由TLS处理）|
| network | ws | WebSocket传输 |
| path | /api/v1/c8f3a2 | WebSocket路径（URL路径，非文件路径）|

> ⚠️ **重要**：`/api/v1/c8f3a2` 是URL路径，不是服务器上真实存在的文件夹！

### Nginx配置

路径：`/etc/nginx/sites-available/default`

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

    # 普通请求转发到Flask网站
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # V2Ray流量转发
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

### 系统服务

```bash
# 查看V2Ray状态
sudo systemctl status v2ray

# 重启V2Ray
sudo systemctl restart v2ray
```

---

## 3. 客户端配置

### Windows（v2rayN）完整参数

| 字段 | 值 | 说明 |
|------|-----|------|
| 别名 | 服务器-VLESS | 备注名称 |
| 地址 | 198.41.203.72 | Cloudflare优选IP |
| 端口 | 443 | HTTPS标准端口 |
| 用户ID | b8e46a10-5287-4b20-a916-0781cd71a60e | UUID |
| 流控 | 空 | VLESS over WebSocket不需要flow |
| 加密方式 | none | VLESS固定为none |
| 传输协议 | ws | WebSocket |
| 伪装域名(host) | qinfuqi.top | 告诉Cloudflare转发到哪个网站 |
| 路径(path) | /api/v1/c8f3a2 | WebSocket路径 |
| 传输层安全 | tls | 开启TLS加密 |
| SNI | qinfuqi.top | SSL证书验证域名 |
| allowInsecure | false | 验证SSL证书 |

### 为什么地址填IP而不是域名？

```
填域名（qinfuqi.top）：
你 → DNS解析 → Cloudflare随机节点（可能很慢）→ 服务器
延迟：982ms  ⚠️

填优选IP（198.41.203.72）：
你 → 直接连接最快的Cloudflare节点 → 服务器
延迟：167ms  ✅

但必须同时填SNI = qinfuqi.top
告诉Cloudflare把请求转发到正确的网站
```

### Android（v2rayNG）配置

参数与Windows完全相同，可通过扫描v2rayN生成的二维码导入。

---

## 4. Cloudflare CDN配置

### DNS记录

| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|---------|
| A | qinfuqi.top | 67.230.164.20 | 🟠 Proxied |
| A | www | 67.230.164.20 | 🟠 Proxied |

### 关键设置

```
SSL/TLS模式：Full
WebSockets：已开启
```

### CDN的作用

```
没有CDN：
GFW扫描 → 发现67.230.164.20在用翻墙协议 → 封锁IP ⚠️

有CDN：
GFW扫描 → 只看到Cloudflare IP → 无法封锁 ✅
（封锁Cloudflare = 封锁全球数百万网站，代价太大）
```

---

## 5. 优选IP配置

### 为什么需要优选IP？

```
Cloudflare全球有数百个节点
默认DNS解析可能分配到很远的节点：
  你 → 美国东部节点 → 绕半个地球 → 洛杉矶服务器
  延迟：982ms  ⚠️

优选IP直接找到离你最近的节点：
  你 → 洛杉矶节点 → 洛杉矶服务器
  延迟：167ms  ✅
```

### 优选工具

```
工具：CloudflareSpeedTest
下载：https://github.com/XIU2/CloudflareSpeedTest/releases/latest
文件：CloudflareST_windows_amd64.zip
```

### 最新测速结果（2026年3月1日）

| IP地址 | 延迟 | 下载速度 | 地区 |
|--------|------|---------|------|
| 104.16.91.9 | 154ms | 86MB/s | LAX ⭐最快 |
| **198.41.203.72** | 155ms | 86MB/s | LAX ✅当前使用 |
| 162.159.38.64 | 155ms | 81MB/s | LAX |
| 104.18.38.170 | 157ms | 83MB/s | LAX |

> 💡 建议每1-2个月重新测速一次，更新优选IP

### 如何更新优选IP

```
1. 运行 CloudflareST.exe
2. 等待测速完成（约5-10分钟）
3. 找到延迟最低、速度最快的IP
4. 在v2rayN配置里更新"地址"字段
5. 保存重新连接
```

---

## 6. 性能指标

### 当前性能

| 指标 | 数值 | 评价 |
|------|------|------|
| 连接延迟 | 167ms | ✅ 正常 |
| 丢包率 | 0% | ✅ 优秀 |
| 理论下载速度 | 86MB/s | ✅ 很快 |
| 节点位置 | 洛杉矶 LAX | ✅ 最优 |
| 线路 | CN2 GIA | ✅ 最优 |

### 延迟优化历程

```
初始（域名直连）：          982ms  ⚠️
关闭CDN（IP直连）：         173ms  ✅
使用优选IP + SNI：          167ms  ✅ 最终方案

总体提升：约6倍！
```

---

## 7. 工作原理详解

### 流量加密过程

```
原始请求：GET https://www.google.com

第一层加密（VLESS）：
把请求包装成VLESS格式

第二层加密（TLS）：
再用TLS加密，变成普通HTTPS流量

第三层伪装（WebSocket）：
伪装成正常的WebSocket连接

GFW看到的：
普通HTTPS请求访问 qinfuqi.top
完全合法，无法识别 ✅
```

### SNI的作用

```
一栋公寓楼（Cloudflare IP：198.41.203.72）
楼里住了数百万个网站

不填SNI：
敲门却不说找谁
Cloudflare不知道转发给谁 ❌

填SNI = qinfuqi.top：
敲门并说"我找qinfuqi.top"
Cloudflare转发到67.230.164.20 ✅
```

### WebSocket路径的作用

```
/api/v1/c8f3a2 是一个URL路径（非文件路径）

普通访问 https://qinfuqi.top/
Nginx → 转发到Flask网站（5000端口）

V2Ray访问 https://qinfuqi.top/api/v1/c8f3a2
Nginx识别路径 → 转发到V2Ray（10000端口）

GFW看到的只是访问一个网站的某个页面
完全正常 ✅
```

---

## 8. 常见问题

### Q：为什么不直接用IP连接，还要绕一圈CDN？

```
直接用IP（67.230.164.20）：
· 速度：173ms ✅
· 风险：IP暴露，随时可能被封 ⚠️
· 被封后：需要付费换IP

使用CDN优选IP（198.41.203.72）：
· 速度：167ms ✅（反而更快！）
· 风险：极低，Cloudflare IP不会被封 ✅
· 被封后：几乎不会发生
```

### Q：Cloudflare优选IP会被封吗？

```
几乎不会！
Cloudflare IP同时服务于全球数百万正规网站
GFW封锁成本极高，基本不会这么做 ✅
```

### Q：本地IP（家里宽带）变化了怎么办？

```
完全不影响！
服务器不认识你的本地IP
服务器只认UUID：b8e46a10-5287-4b20-a916-0781cd71a60e
本地IP随便变 ✅
```

### Q：连接突然变慢怎么办？

```
第一步：检查是否高峰期（晚上8-11点）
        → 高峰期联通国际出口拥堵，属正常现象

第二步：重新运行CloudflareST测速
        → 更新优选IP

第三步：检查服务是否正常
        sudo systemctl status v2ray nginx
```

### Q：服务器重启后怎么办？

```
三个服务都已配置开机自启：
✅ v2ray.service
✅ nginx.service  
✅ blog.service

服务器重启后自动恢复，无需任何操作
```

---

## 9. 定期维护

### 每1-2个月

```bash
# 重新测速，更新优选IP
# Windows运行：
CloudflareST.exe

# 更新v2rayN里的地址字段
```

### 每3-6个月

```bash
# 检查V2Ray是否有新版本
v2ray version

# 检查系统更新
sudo apt update && sudo apt upgrade -y  # Ubuntu
sudo dnf update -y  # AlmaLinux
```

### 随时检查服务状态

```bash
# 查看三个核心服务
sudo systemctl status v2ray nginx blog

# 查看V2Ray日志
sudo journalctl -u v2ray -f

# 查看Nginx访问日志
sudo tail -f /var/log/nginx/access.log
```

---

## 附录：协议升级路线图

```
已完成：
VMess + WebSocket  →  VLESS + WebSocket  ✅

未来可选升级：
VLESS + WebSocket  →  VLESS + XHTTP H2
优点：更好的伪装，更难被识别
难度：中等，需要修改服务器和客户端配置

VLESS + XHTTP H2  →  VLESS + XHTTP H3
优点：最新最快，GFW最难识别
难度：较复杂
```

> 当前VLESS + WebSocket方案稳定可用，如无被封问题无需急于升级。
