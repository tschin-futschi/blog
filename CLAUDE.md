# CLAUDE.md — 项目指南

## 项目简介

**Tschin Futschi 的个人博客**（博主：Qinfuqi / 秦甫琦）

基于 Flask 的中文个人博客，内容以 AI、金融、体育、HR 等领域的资讯简报为主，辅以手动撰写文章。爬虫每日自动从 RSS 源抓取内容生成 Markdown 简报，Flask 读取文件并渲染展示。目标是做成一个**专业的个人博客网站**。

---

## 技术栈

- **后端**: Python 3, Flask 3, SQLAlchemy (SQLite 本地 / MySQL 生产)
- **内容**: Markdown 文件 + YAML front matter（python-markdown 渲染）
- **数据库**: SQLite (`blog.db`)，仅存元数据 + 阅读量，文章内容来自文件系统
- **爬虫**: feedparser + requests，抓取 RSS，生成 .md 文件
- **前端**: 原生 HTML/CSS/JS，无框架；毛玻璃设计风格，支持暗黑模式
- **部署**: Linux 服务器，systemd 管理，venv 环境，路径 `/home/echo/blog`

---

## 目录结构

```
blog/
├── app.py                  # Flask 主应用（路由、解析、搜索、管理后台）
├── models.py               # SQLAlchemy 模型（Post, Tag, ViewLog, SearchIndex）
├── database.py             # DB 初始化、同步、查询、阅读量统计
├── sync_db.py              # 手动同步 MD 文件到数据库的脚本
├── migrate_to_db.py        # 历史迁移脚本
├── requirements.txt        # 依赖（flask, markdown, pyyaml, pygments, flask-sqlalchemy）
├── blog.db                 # SQLite 数据库
│
├── posts/                  # 文章内容（按分类子目录）
│   ├── ai/
│   ├── finance/
│   ├── sports/
│   └── hr/
│
├── crawlers/               # RSS 爬虫
│   ├── fetch_news.py       # 通用爬虫主程序（--config 指定分类）
│   ├── run.sh              # 统一启动脚本（bash run.sh ai / all）
│   ├── ai/ai_config.json
│   ├── finance/finance_config.json
│   ├── sports/sports_config.json
│   └── hr/hr_config.json
│
├── templates/              # Jinja2 模板
│   ├── base.html           # 公共布局（header, footer, 搜索框）
│   ├── categories.html     # 首页（分类卡片 + 最新文章）
│   ├── index.html          # 文章列表（带标签/分类过滤）
│   ├── post.html           # 文章详情（TOC 侧边栏）
│   ├── 404.html
│   └── admin/              # 后台管理页面
│
├── static/
│   ├── css/style.css       # 全部前端样式（CSS 变量体系）
│   ├── css/admin.css       # 后台专用样式
│   └── js/
│       ├── search.js       # 实时搜索（防抖 + 高亮）
│       └── header-scroll.js # 滚动时 header 压缩效果
│
└── kexueshangwang/         # 服务器配置文档（与博客无关，忽略）
```

---

## 关键约定

### 文章 slug 规则
slug 为相对于 `posts/` 的路径，不含 `.md` 后缀。
例：`posts/ai/2026-03-01-ai-news-digest.md` → slug = `ai/2026-03-01-ai-news-digest`

### 分类映射
分类名 = `posts/` 下的子目录名（英文）。
前端图标映射在 `app.py` 的 `CAT_ICONS` 字典中。
中文名映射尚未统一实现，是待办项。

### 数据库与文件的关系
- **文章内容**：始终以文件系统为准（`.md` 文件）
- **数据库**：只存 slug、阅读量（`views`）、标签索引等元数据
- 新文章需手动或通过管理后台"同步"才会进入 DB，但读取文章不依赖 DB

### 爬虫配置格式（JSON）
```json
{
  "sources": [{"name": "...", "name_zh": "...", "url": "...", "lang": "en/zh"}],
  "keywords": {"en": [...], "zh": [...]},
  "title_zh": "...", "title_en": "...",
  "tags": [...],
  "slug": "xxx-news-digest"
}
```

### 环境变量
- `FLASK_SECRET_KEY`：生产环境必须设置，否则重启后 session 失效
- `DATABASE_URL`：可选，不设则用 SQLite

---

## 开发命令

```bash
# 本地启动
cd /path/to/blog
source venv/bin/activate
python app.py

# 安装依赖
pip install -r requirements.txt

# 手动运行爬虫（在博客根目录执行）
python crawlers/fetch_news.py --config crawlers/ai/ai_config.json

# 同步文章到数据库
python sync_db.py

# 生产服务器（Linux）
systemctl restart blog
systemctl status blog

# 服务器路径
/home/echo/blog
venv: /home/echo/blog/venv/bin/python3
```

---

## 路由总览

| 路由 | 功能 |
|------|------|
| `GET /` 或 `/blog` | 首页（分类卡片 + 最新文章） |
| `GET /blog/posts` | 全部文章列表 |
| `GET /blog/category/<cat>` | 分类过滤列表 |
| `GET /blog/tag/<tag>` | 标签过滤列表 |
| `GET /blog/<path:slug>` | 文章详情 |
| `GET /blog/search?q=` | 搜索 API（返回 JSON） |
| `GET /admin` | 后台首页（需登录） |
| `GET/POST /admin/new` | 新建文章 |
| `GET/POST /admin/edit/<slug>` | 编辑文章 |
| `POST /admin/delete/<slug>` | 删除文章 |
| `POST /admin/upload` | 上传 .md 文件 |
| `GET/POST /admin/users` | 用户管理 |
| `GET /admin/database` | DB 统计 |
| `GET /admin/terminal` | 在线终端（命令白名单） |

---

## 当前目标：打造专业博客

按优先级排列的待办项：

### 第一阶段（核心专业感）
- [ ] 重做首页：加入 Hero 区域，展示博主身份和定位
- [ ] 新增 About / 关于 页面
- [ ] SEO 完善：每页 meta description、Open Graph 标签
- [ ] 分类中文名映射（前端展示）

### 第二阶段（功能完善）
- [ ] RSS 订阅输出（`/feed.xml`）
- [ ] 文章阅读时间估算（字数 / 300 字每分钟）
- [ ] 文章列表分页
- [ ] 移动端汉堡菜单

### 第三阶段（互动与增长）
- [ ] 评论系统（Giscus，基于 GitHub Discussions）
- [ ] 站点统计页面（阅读量榜单）

### 代码质量
- [ ] `clean_html()` 在 `app.py` 和 `crawlers/fetch_news.py` 各定义一份，考虑提取到公共模块

---

## 注意事项

- **不要修改 `kexueshangwang/` 目录**，这是服务器配置文档，与博客代码无关
- **不要动 `blog.db`**，这是生产数据库文件，应通过代码操作
- CSS 全部在 `static/css/style.css` 中，使用 CSS 变量体系，新增样式也写在这里，不要创建新 CSS 文件
- 模板继承自 `base.html`，新增页面也继承它
- 后台路由均需 `@login_required` 装饰器
- 在线终端的命令白名单在 `app.py` 的 `TERMINAL_WHITELIST` 列表中
