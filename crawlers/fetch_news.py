#!/usr/bin/env python3
"""
资讯简报生成器（通用版）
通过 --config 参数指定配置文件，支持任意分类

用法:
  python crawlers/fetch_news.py --config crawlers/ai/ai_config.json
  python crawlers/fetch_news.py --config crawlers/finance/finance_config.json

目录结构:
  blog/
  ├── crawlers/
  │   ├── fetch_news.py               ← 本文件（通用）
  │   ├── ai/
  │   │   └── ai_config.json
  │   └── finance/
  │       └── finance_config.json
  ├── logs/
  └── posts/
      ├── ai/
      └── finance/
"""

import os
import re
import sys
import json
import argparse
import datetime
import logging
import feedparser
import requests

VERIFY_SSL = True

# ── 命令行参数 ────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="资讯简报生成器")
parser.add_argument("--config", required=True, help="配置文件路径，相对于博客根目录，例如 crawlers/ai/ai_config.json")
args = parser.parse_args()

# ── 路径配置 ─────────────────────────────────────────────────────────────────

# fetch_news.py 在 blog/crawlers/ 里，上一级是 crawlers/，再上一级是 blog/
BLOG_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BLOG_ROOT, args.config)

if not os.path.exists(CONFIG_FILE):
    print(f"错误：配置文件不存在: {CONFIG_FILE}")
    sys.exit(1)

# 从配置文件路径推断分类名，例如 crawlers/ai/ai_config.json → ai
CATEGORY  = os.path.basename(os.path.dirname(CONFIG_FILE))
POSTS_DIR = os.path.join(BLOG_ROOT, "posts", CATEGORY)
LOG_DIR   = os.path.join(BLOG_ROOT, "logs")

# ── 日志配置 ─────────────────────────────────────────────────────────────────

os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"{CATEGORY}_fetch_{datetime.date.today().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


# ── 加载配置 ─────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info(f"成功加载配置文件 [{CATEGORY}]，共 {len(config['sources'])} 个来源")
    return config


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def is_relevant(text: str, lang: str, keywords: dict) -> bool:
    """判断文章是否与关键词相关"""
    text_lower = text.lower()
    kw_list = keywords.get(lang, keywords.get("en", []))
    return any(kw.lower() in text_lower for kw in kw_list)


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def truncate(text: str, max_len: int = 150) -> str:
    text = clean_html(text)
    return text[:max_len].rstrip() + "..." if len(text) > max_len else text


def fetch_feed(source: dict, keywords: dict) -> list:
    """抓取单个 RSS 源"""
    articles = []
    try:
        logger.info(f"正在抓取: {source['name_zh']} ({source['url']})")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsFetcher/1.0)"}
        response = requests.get(source["url"], headers=headers, timeout=15, verify=VERIFY_SSL)
        logger.debug(f"HTTP 状态码: {response.status_code}")

        feed = feedparser.parse(response.content)
        total_entries = len(feed.entries)
        logger.debug(f"RSS 解析到 {total_entries} 条条目")

        if total_entries == 0:
            logger.warning(f"警告: {source['name_zh']} 没有解析到任何条目，请检查 RSS 地址是否有效")

        seen_titles = set()
        for entry in feed.entries[:10]:
            title   = clean_html(entry.get("title", ""))
            summary = truncate(entry.get("summary", entry.get("description", "")))
            link    = entry.get("link", "")

            # 简单去重
            if title in seen_titles:
                continue
            seen_titles.add(title)

            logger.debug(f"  检查文章: {title[:60]}")
            if not is_relevant(title + " " + summary, source["lang"], keywords):
                logger.debug(f"  -> 跳过（不相关）")
                continue

            logger.debug(f"  -> 收录！")
            articles.append({
                "title":     title,
                "summary":   summary,
                "link":      link,
                "source":    source["name"],
                "source_zh": source["name_zh"],
                "lang":      source["lang"],
            })

        logger.info(f"完成 {source['name_zh']}: 收录 {len(articles)} 条")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"网络连接失败 {source['name_zh']}: {e}")
    except requests.exceptions.Timeout:
        logger.error(f"请求超时 {source['name_zh']}")
    except Exception as e:
        logger.error(f"抓取失败 {source['name_zh']}: {type(e).__name__}: {e}")

    return articles


def generate_markdown(articles: list, date: datetime.date, config: dict) -> str:
    """生成中英双语 Markdown 简报，标题和标签从配置文件读取"""
    date_str = date.strftime("%Y-%m-%d")
    date_zh  = date.strftime("%Y年%m月%d日")

    title_zh = config.get("title_zh", f"{CATEGORY} 资讯简报")
    title_en = config.get("title_en", f"{CATEGORY.capitalize()} News Digest")
    tags     = config.get("tags", [CATEGORY, "简报"])
    summary  = config.get("summary_tpl", "{date_zh} {title_zh}汇总").format(
                   date_zh=date_zh, title_zh=title_zh)

    en_articles = [a for a in articles if a["lang"] == "en"]
    zh_articles = [a for a in articles if a["lang"] == "zh"]

    slug_name = config.get("slug", f"{CATEGORY}-news-digest")

    lines = [
        f"---",
        f"title: {title_zh} | {title_en} {date_str}",
        f"date: {date_str}",
        f"tags: {tags}",
        f"summary: {summary}",
        f"---",
        f"",
        f"# {title_zh} | {title_en}",
        f"",
        f"> 日期: {date_zh} | 自动抓取自 {len(set(a['source'] for a in articles))} 个来源，共 {len(articles)} 条资讯",
        f"",
        f"---",
        f"",
    ]

    if zh_articles:
        lines += [f"## 国内资讯", f""]
        for i, a in enumerate(zh_articles, 1):
            lines += [
                f"### {i}. {a['title']}",
                f"",
                f"- **来源**: {a['source_zh']}",
                f"- **链接**: [{a['link']}]({a['link']})",
                f"- **摘要**: {a['summary']}",
                f"",
            ]

    if en_articles:
        lines += [f"## International News", f""]
        for i, a in enumerate(en_articles, 1):
            lines += [
                f"### {i}. {a['title']}",
                f"",
                f"- **Source**: {a['source']}",
                f"- **Link**: [{a['link']}]({a['link']})",
                f"- **Summary**: {a['summary']}",
                f"",
            ]

    lines += [
        f"---",
        f"",
        f"*本简报由自动脚本生成 | Auto-generated by fetch_news.py*",
    ]

    return "\n".join(lines)


def save_post(content: str, date: datetime.date, config: dict) -> str:
    """保存为 Markdown 文件"""
    os.makedirs(POSTS_DIR, exist_ok=True)
    date_str  = date.strftime("%Y-%m-%d")
    slug_name = config.get("slug", f"{CATEGORY}-news-digest")
    filename  = f"{date_str}-{slug_name}.md"
    filepath  = os.path.join(POSTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


# ── 主程序 ───────────────────────────────────────────────────────────────────

def main():
    today = datetime.date.today()
    logger.info("=" * 50)
    logger.info(f"开始抓取 [{CATEGORY}] 资讯简报 ({today})")
    logger.info(f"文章保存至: {POSTS_DIR}")
    logger.info("=" * 50)

    config   = load_config()
    sources  = config["sources"]
    keywords = config["keywords"]

    all_articles = []
    for source in sources:
        articles = fetch_feed(source, keywords)
        all_articles.extend(articles)

    logger.info(f"共收录 {len(all_articles)} 条相关资讯")

    if not all_articles:
        logger.warning("没有抓取到任何文章，请检查网络连接或 RSS 地址是否有效")
        return

    content  = generate_markdown(all_articles, today, config)
    filename = save_post(content, today, config)
    logger.info(f"简报已保存：posts/{CATEGORY}/{filename}")
    logger.info(f"日志已保存至: {log_filename}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
