# Tschin Futschi 的个人博客

> 秦福麒（Qinfuqi）的个人博客，关注 AI 前沿、金融市场、体育赛事与人力资源，每日整理行业资讯简报。

基于 Flask 构建，支持 Markdown 文章、RSS 自动抓取、分类管理与后台管理。

## 目录结构

```
blog/
├── app.py                  # Flask 主应用（路由、解析、搜索、管理后台）
├── models.py               # SQLAlchemy 模型（Post, Tag, ViewLog）
├── database.py             # DB 初始化、同步、阅读量统计
├── sync_db.py              # 手动同步 MD 文件到数据库
├── requirements.txt        # Python 依赖
├── blog.db                 # SQLite 数据库（元数据 + 阅读量）
│
├── posts/                  # 文章内容（按分类子目录）
│   ├── ai/
│   ├── finance/
│   ├── sports/
│   └── hr/
│
├── crawlers/               # RSS 爬虫
│   ├── fetch_news.py       # 通用爬虫（--config 指定分类）
│   ├── run.sh              # 统一启动脚本
│   ├── ai/ai_config.json
│   ├── finance/finance_config.json
│   ├── sports/sports_config.json
│   └── hr/hr_config.json
│
├── templates/              # Jinja2 模板
│   ├── base.html           # 公共布局
│   ├── categories.html     # 首页（Hero + 分类卡片 + 最新文章）
│   ├── index.html          # 文章列表
│   ├── post.html           # 文章详情（TOC 侧边栏）
│   ├── 404.html
│   └── admin/              # 后台管理页面
│
└── static/
    ├── css/style.css       # 全部前端样式（唯一样式文件）
    ├── css/admin.css       # 后台专用样式
    └── js/
        ├── search.js           # 实时搜索（防抖 + 高亮）
        └── header-scroll.js    # Header 滚动效果 + 移动端菜单
```

## 功能

- ✅ 首页 Hero 区域（博主身份展示）
- ✅ 文章分类（多分类子目录）
- ✅ 文章列表，按日期倒序
- ✅ 标签筛选
- ✅ 实时搜索（多权重评分 + 关键词高亮）
- ✅ 上一篇 / 下一篇导航
- ✅ 文章目录侧边栏（TOC）
- ✅ 移动端响应式布局 + 汉堡菜单
- ✅ 毛玻璃设计风格 + 暗黑模式
- ✅ 后台管理（新建、编辑、删除、上传文章）
- ✅ 阅读量统计（IP + UA 去重）
- ✅ 每日自动抓取多分类资讯简报

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 本地启动
python app.py
# 访问 http://localhost:5000
```

## 爬虫

支持 AI、金融、体育、HR 四个分类，文件名时间戳精确到分钟。

```bash
# 运行单个分类
python crawlers/fetch_news.py --config crawlers/ai/ai_config.json

# 运行所有分类
bash crawlers/run.sh all
```

爬虫配置文件（来源、关键词）在各分类目录下的 `*_config.json` 中。

## 部署（Linux 服务器）

```bash
# 拉取最新代码
cd /home/echo/blog
git pull

# 重启服务
systemctl restart blog
systemctl status blog
```

服务由 systemd 管理，venv 路径：`/home/echo/blog/venv`。

## 文章格式

文章为 Markdown 文件，存放在 `posts/<分类>/` 目录，文件名格式：

```
YYYY-MM-DD-HHMM-slug.md
```

Front matter 示例：

```yaml
---
title: 文章标题
date: 2026-03-08 14:30
tags: [AI, 大模型, 技术]
summary: 一句话摘要（可选）
---
```
