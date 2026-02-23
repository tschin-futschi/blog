# Flask 个人博客

## 项目结构

```
blog/
├── app.py                  # Flask 主程序
├── requirements.txt        # 依赖
├── posts/                  # Markdown 文章目录
│   └── 2024-06-01-hello-world.md
├── templates/
│   ├── base.html           # 公共布局
│   ├── index.html          # 文章列表页
│   ├── post.html           # 文章详情页
│   └── 404.html
└── static/
    ├── css/style.css
    └── js/search.js
```

## 安装与启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动开发服务器
python app.py

# 3. 生产环境（推荐用 gunicorn）
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

## 写博客

在 `posts/` 文件夹中新建 `.md` 文件，文件名格式：

```
YYYY-MM-DD-slug名称.md
```

文件头部加 Front Matter：

```markdown
---
title: 文章标题
date: 2024-06-01
tags: [标签1, 标签2]
summary: 文章摘要，显示在列表页（可选，不填则自动截取正文前120字）
---

正文从这里开始...
```

## 功能

- ✅ 文章列表，按日期倒序
- ✅ 文章详情，Markdown 渲染（支持代码高亮、表格、目录）
- ✅ 标签筛选
- ✅ 实时搜索
- ✅ 上一篇 / 下一篇导航
- ✅ 响应式布局（移动端友好）
