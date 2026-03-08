# CLAUDE.md — 项目指南

## 项目简介

**Tschin Futschi 的个人博客**（博主：Qinfuqi / 秦福麒）

基于 Flask 的中文个人博客，内容以 AI、金融、体育、HR 等领域的资讯简报为主，辅以手动撰写文章。爬虫每日自动从 RSS 源抓取内容生成 Markdown 简报，Flask 读取文件并渲染展示。目标是做成一个**专业的个人博客网站**。

---

## 技术栈

- **后端**: Python 3, Flask 3, SQLAlchemy（SQLite 本地 / MySQL 生产）
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
├── blog.db                 # SQLite 数据库（勿直接修改）
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
│   └── admin/              # 后台管理页面（base/database/edit/index/login/terminal/users）
│
├── static/
│   ├── css/style.css       # 全部前端样式（CSS 变量体系，唯一样式文件）
│   ├── css/admin.css       # 后台专用样式
│   └── js/
│       ├── search.js       # 实时搜索（防抖 + 高亮）
│       └── header-scroll.js # 滚动时 header 压缩效果
│
└── kexueshangwang/         # ⚠️ 服务器配置文档，与博客无关，不要修改或读取
```

---

## 核心数据流

```
RSS 源
  └─→ crawlers/fetch_news.py（feedparser 抓取 + 关键词过滤）
        └─→ posts/<category>/<date>-<slug>.md（YAML front matter + Markdown 正文）
              └─→ app.py: parse_post()（实时解析，文件系统为权威数据源）
                    └─→ Jinja2 模板渲染
              └─→ blog.db（仅存 slug、views 等元数据，需手动 sync 或后台同步）
```

**关键原则：文章内容以 `.md` 文件为准，数据库只是元数据缓存。**

---

## 关键约定

### 文章 slug 规则
slug 为相对于 `posts/` 的路径，不含 `.md` 后缀。
例：`posts/ai/2026-03-01-ai-news-digest.md` → slug = `ai/2026-03-01-ai-news-digest`

### Markdown front matter 格式
```yaml
---
title: 文章标题
date: 2026-03-01
tags: [AI, 大模型, 技术]
summary: 一句话摘要（可选，不填则取正文前120字）
---
```

### 分类体系
- 分类名 = `posts/` 下的子目录名（英文）
- 图标映射：`app.py` → `CAT_ICONS` 字典
- 中文名映射：`app.py` → `CAT_NAMES` 字典
- 现有分类：`ai`, `finance`, `sports`, `hr`, `general`, `tech`, `life`, `travel`, `book`, `news`

### 爬虫配置 JSON 格式
```json
{
  "sources": [{"name": "来源名", "name_zh": "中文名", "url": "RSS链接", "lang": "en/zh"}],
  "keywords": {"en": ["keyword1"], "zh": ["关键词1"]},
  "title_zh": "中文标题",
  "title_en": "English Title",
  "tags": ["tag1", "tag2"],
  "slug": "xxx-news-digest"
}
```

### 环境变量
- `FLASK_SECRET_KEY`：**生产环境必须设置**，否则重启后 session 失效
- `DATABASE_URL`：可选，不设则使用 SQLite（`blog.db`）

---

## 代码规范（修改代码时必须遵守）

### Python
- 遵循现有代码风格：函数注释用中文，类型注解保持一致
- 工具函数（如 `clean_html`）统一放在 `app.py` 的「工具函数」区块，**不要在爬虫中重复定义**
- 新路由必须加 `@login_required` 装饰器（管理后台）
- 禁止：直接操作 `blog.db` 文件；应通过 SQLAlchemy ORM

### HTML/CSS
- **所有样式写在 `static/css/style.css`，不要创建新 CSS 文件**
- 使用现有 CSS 变量体系（`--bg-primary`、`--text-primary`、`--accent` 等）
- 新页面模板必须 `{% extends "base.html" %}`
- 暗黑模式通过 CSS 变量自动适配，不要写 `[data-theme="dark"]` 的专属覆盖样式

### 前端交互
- 无框架，使用原生 JS（ES6+）
- 新增 JS 逻辑写在 `static/js/` 下单独文件，或内联在对应模板的 `{% block scripts %}` 中

---

## 开发命令

```bash
# 本地启动
cd /path/to/blog
source venv/bin/activate
python app.py                    # 默认 http://0.0.0.0:5000

# 安装依赖
pip install -r requirements.txt

# 手动运行爬虫（必须在博客根目录执行）
python crawlers/fetch_news.py --config crawlers/ai/ai_config.json
python crawlers/fetch_news.py --config crawlers/finance/finance_config.json
bash crawlers/run.sh all         # 运行所有爬虫

# 同步文章到数据库
python sync_db.py

# 生产服务器
systemctl restart blog
systemctl status blog
```

---

## 路由总览

| 路由 | 方法 | 功能 | 需登录 |
|------|------|------|--------|
| `/` 或 `/blog` | GET | 首页（分类卡片 + 最新文章） | ❌ |
| `/blog/posts` | GET | 全部文章列表 | ❌ |
| `/blog/category/<cat>` | GET | 分类过滤列表 | ❌ |
| `/blog/tag/<tag>` | GET | 标签过滤列表 | ❌ |
| `/blog/<path:slug>` | GET | 文章详情（TOC 侧边栏） | ❌ |
| `/blog/search?q=` | GET | 搜索 API（返回 JSON） | ❌ |
| `/admin` | GET | 后台首页 | ✅ |
| `/admin/new` | GET/POST | 新建文章 | ✅ |
| `/admin/edit/<slug>` | GET/POST | 编辑文章 | ✅ |
| `/admin/delete/<slug>` | POST | 删除文章 | ✅ |
| `/admin/upload` | POST | 上传 .md 文件 | ✅ |
| `/admin/users` | GET/POST | 用户管理 | ✅ |
| `/admin/database` | GET | DB 统计与阅读量排行 | ✅ |
| `/admin/terminal` | GET/POST | 在线终端（命令白名单） | ✅ |

---

## 待办事项（按优先级）

### 🔴 第一阶段（核心专业感）
- [ ] 重做首页：加入 Hero 区域，展示博主身份和定位
- [ ] 新增 About / 关于 页面（路由：`/about`）
- [ ] SEO 完善：每页 `<meta description>` 和 Open Graph 标签
- [ ] 分类中文名在前端统一展示（`CAT_NAMES` 已定义，待模板使用）

### 🟡 第二阶段（功能完善）
- [ ] RSS 订阅输出（路由：`/feed.xml`）
- [ ] 文章阅读时间估算（字数 ÷ 300 字/分钟，前端展示）
- [ ] 文章列表分页（每页 10 篇）
- [ ] 移动端汉堡菜单

### 🟢 第三阶段（互动与增长）
- [ ] 评论系统（Giscus，基于 GitHub Discussions）
- [ ] 站点统计页面（阅读量榜单，路由：`/stats`）

### 🔧 代码质量
- [ ] `clean_html()` 在 `app.py` 和 `crawlers/fetch_news.py` 各定义一份 → 提取到公共模块 `utils.py`
- [ ] 搜索功能迁移到数据库全文检索（当前为逐文件扫描，文章多时性能差）

---

## ⚠️ 注意事项（不要踩的坑）

1. **不要修改 `kexueshangwang/` 目录**，这是服务器配置文档，与博客代码无关
2. **不要直接操作 `blog.db`**，这是生产数据库，通过 ORM 或 `sync_db.py` 操作
3. **CSS 只写在 `static/css/style.css`**，不要新建 CSS 文件
4. **新增页面必须继承 `base.html`**，保证 header/footer/搜索框统一
5. **后台所有路由加 `@login_required`**
6. **在线终端的命令白名单**在 `app.py` 的 `TERMINAL_WHITELIST` 列表中，新增命令必须在此显式添加
7. **爬虫必须从博客根目录运行**（路径依赖 `BLOG_ROOT` 推导）
