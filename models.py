"""
数据库模型定义
使用 SQLAlchemy ORM 管理 MySQL/SQLite 数据库
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# ── 文章表 ─────────────────────────────────────────────────────────────────────
class Post(db.Model):
    """文章模型"""
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text)
    content_html = db.Column(db.Text)  # Markdown 转换后的 HTML
    content_raw = db.Column(db.Text)   # 原始 Markdown 内容
    filepath = db.Column(db.String(500))  # 原始文件路径

    # 分类与标签
    category = db.Column(db.String(50), nullable=False, index=True)
    tags = db.relationship('Tag', secondary='post_tags', backref='posts')

    # 元数据
    date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 统计数据
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Post {self.title}>'


# ── 标签表 ─────────────────────────────────────────────────────────────────────
class Tag(db.Model):
    """标签模型"""
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Tag {self.name}>'


# ── 文章-标签关联表 ───────────────────────────────────────────────────────────
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


# ── 阅读统计表 ───────────────────────────────────────────────────────────────
class ViewLog(db.Model):
    """阅读日志模型"""
    __tablename__ = 'view_logs'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    post = db.relationship('Post', backref='view_logs')


# ── 搜索索引表（可选，用于全文搜索）─────────────────────────────────────────
class SearchIndex(db.Model):
    """搜索索引模型"""
    __tablename__ = 'search_index'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), unique=True, nullable=False)
    content_text = db.Column(db.Text)  # 所有可搜索的文本内容
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    post = db.relationship('Post', backref='search_index')
