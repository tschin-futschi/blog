# Qinfuqi's Blog

基于 Flask 的个人博客，支持 Markdown 文章、自动资讯抓取和分类管理。

## 项目结构
```
blog/
├── app.py                      # Flask 主程序
├── requirements.txt            # 依赖
├── crawlers/                   # 爬虫脚本目录
│   └── ai/                     # AI 资讯爬虫
│       ├── ai_fetch_news.py    # 抓取脚本
│       ├── ai_config.json      # 配置文件（来源、关键词）
│       └── ai_run.sh           # 定时任务启动脚本
├── posts/                      # Markdown 文章目录
│   └── ai/                     # AI 资讯简报
├── templates/                  # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── post.html
│   ├── 404.html
│   └── admin/
└── static/                     # 静态资源
    ├── css/style.css
    └── js/search.js
```

## 功能

- ✅ 文章列表，按日期倒序
- ✅ 文章分类（支持子目录）
- ✅ 标签筛选
- ✅ 实时搜索
- ✅ 上一篇 / 下一篇导航
- ✅ 响应式布局
- ✅ 后台管理（新建、编辑、删除文章）
- ✅ 每天自动抓取 AI 资讯简报

## 自动抓取

每天早上 08:05 北京时间（次日） 00：05 美西时间 自动运行 `crawlers/ai/ai_run.sh`，抓取 AI 相关新闻生成 Markdown 简报，保存到 `posts/ai/` 目录。

新闻来源在 `crawlers/ai/ai_config.json` 中配置，可以自由添加或删除。
