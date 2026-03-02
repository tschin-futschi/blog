#!/usr/bin/env python3
"""
快速数据库同步脚本
用于爬虫运行后快速同步新文章到数据库
"""

import os
import sys

def main():
    print("快速同步数据库...")

    try:
        # 导入数据库模块
        from database import sync_posts_from_files
        from models import db
        from app import app, POSTS_DIR

        with app.app_context():
            # 同步文章
            sync_posts_from_files(POSTS_DIR)
            print("✓ 同步完成")

    except Exception as e:
        print(f"✗ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
