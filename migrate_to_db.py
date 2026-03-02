#!/usr/bin/env python3
"""
数据库迁移脚本
将现有的 Markdown 文件同步到数据库
"""

import os
import sys
from database import sync_posts_from_files
from models import db, Post, Tag, ViewLog, SearchIndex
from app import app

def main():
    print("开始数据库迁移...")
    print("-" * 50)

    # 同步文章
    print("1. 同步文章到数据库...")
    from app import POSTS_DIR

    with app.app_context():
        # 创建所有表
        db.create_all()
        sync_posts_from_files(POSTS_DIR)

    print("-" * 50)
    print("✓ 数据库迁移完成！")
    print(f"✓ 数据库文件位于: {os.path.join(os.path.dirname(__file__), 'blog.db')}")
    print("\n提示：如果需要重新同步，可以删除 blog.db 后重新运行此脚本。")

if __name__ == "__main__":
    main()
