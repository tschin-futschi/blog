"""
数据库配置和管理
"""

import os
from datetime import datetime
from flask import Flask
from models import db, Post, Tag, ViewLog, SearchIndex


def init_database(app: Flask):
    """初始化数据库"""
    # 配置数据库连接
    # 优先使用环境变量，否则使用 SQLite
    if os.environ.get('DATABASE_URL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    else:
        # 使用 SQLite 作为默认数据库
        db_path = os.path.join(os.path.dirname(__file__), 'blog.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False  # 设置为 True 可以看到 SQL 语句

    # 初始化数据库
    db.init_app(app)

    # 创建所有表
    with app.app_context():
        db.create_all()

    return db


def sync_posts_from_files(posts_dir: str):
    """
    从 Markdown 文件同步文章到数据库
    这个函数可以手动调用或作为迁移脚本
    """
    from app import parse_post, get_all_posts

    print("开始同步文章到数据库...")

    posts = get_all_posts()
    for post_data in posts:
        # 检查文章是否已存在
        existing = Post.query.filter_by(slug=post_data['slug']).first()

        if existing:
            # 更新现有文章
            existing.title = post_data['title']
            existing.summary = post_data['summary']
            existing.content_html = post_data['content']
            existing.content_raw = post_data['raw']
            existing.filepath = post_data['filepath']
            existing.category = post_data['category']
            existing.date = post_data['date']
            existing.updated_at = datetime.utcnow()

            # 更新标签
            existing.tags.clear()
            for tag_name in post_data['tags']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                existing.tags.append(tag)

            print(f"更新文章: {post_data['title']}")
        else:
            # 创建新文章
            post = Post(
                slug=post_data['slug'],
                title=post_data['title'],
                summary=post_data['summary'],
                content_html=post_data['content'],
                content_raw=post_data['raw'],
                filepath=post_data['filepath'],
                category=post_data['category'],
                date=post_data['date']
            )

            db.session.add(post)
            db.session.flush()  # 获取 post.id

            # 添加标签
            for tag_name in post_data['tags']:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)

            print(f"创建文章: {post_data['title']}")
            existing = post

        # 更新搜索索引
        search_text = f"{post_data['title']} {post_data['summary']} {post_data['raw']}"
        search_index = SearchIndex.query.filter_by(post_id=existing.id).first()
        if search_index:
            search_index.content_text = search_text
        else:
            search_index = SearchIndex(post_id=existing.id, content_text=search_text)
            db.session.add(search_index)

    db.session.commit()
    print(f"同步完成！共处理 {len(posts)} 篇文章。")


def get_post_from_db(slug: str):
    """从数据库获取文章"""
    return Post.query.filter_by(slug=slug).first()


def get_posts_from_db(category: str = None, tag: str = None, limit: int = None):
    """从数据库获取文章列表"""
    query = Post.query

    if category:
        query = query.filter_by(category=category)

    if tag:
        query = query.join(Post.tags).filter(Tag.name == tag)

    query = query.order_by(Post.date.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def search_in_db(query: str, limit: int = 20):
    """在数据库中搜索"""
    from sqlalchemy import or_, func

    search_term = f"%{query.lower()}%"

    # 搜索标题、摘要和内容
    posts = Post.query.filter(
        or_(
            Post.title.ilike(search_term),
            Post.summary.ilike(search_term),
            Post.content_raw.ilike(search_term)
        )
    ).order_by(Post.date.desc()).limit(limit).all()

    return posts


def increment_views(post_id: int, ip_address: str = None, user_agent: str = None):
    """增加文章阅读量"""
    post = Post.query.get(post_id)
    if post:
        post.views += 1

        # 记录阅读日志
        log = ViewLog(
            post_id=post_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)

        db.session.commit()

    return post.views
