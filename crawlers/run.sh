#!/bin/bash
# 统一资讯抓取脚本
# 用法: bash crawlers/run.sh ai
#       bash crawlers/run.sh finance
#       bash crawlers/run.sh all

BLOG_DIR="/home/echo/blog"
PYTHON="$BLOG_DIR/venv/bin/python3"
SCRIPT="$BLOG_DIR/crawlers/fetch_news.py"

run_crawler() {
    CATEGORY=$1
    CONFIG="$BLOG_DIR/crawlers/$CATEGORY/${CATEGORY}_config.json"
    if [ ! -f "$CONFIG" ]; then
        echo "错误：配置文件不存在: $CONFIG"
        return 1
    fi
    echo "▶ 开始抓取 [$CATEGORY]..."
    cd "$BLOG_DIR"
    $PYTHON $SCRIPT --config "crawlers/$CATEGORY/${CATEGORY}_config.json"
    echo "✓ [$CATEGORY] 完成"
}

TARGET=${1:-all}

if [ "$TARGET" = "all" ]; then
    for dir in "$BLOG_DIR/crawlers"/*/; do
        CATEGORY=$(basename "$dir")
        run_crawler "$CATEGORY"
    done
else
    run_crawler "$TARGET"
fi
