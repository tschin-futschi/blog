#!/usr/bin/env python3
"""
AI 资讯简报生成器
每天自动抓取 AI 相关新闻，生成中英双语 Markdown 简报

目录结构:
  blog/
  ├── crawlers/ai/
  │   ├── ai_fetch_news.py   ← 本文件
  │   └── ai_config.json
  ├── logs/
  │   └── ai_fetch_news_YYYY-MM-DD.log
  └── posts/
      └── ai/
          └── YYYY-MM-DD-ai-news-digest.md
"""

import os
import re
import json
import datetime
import logging
import feedparser
import requests
import urllib3

# 禁用 SSL 警告（仅在公司网络测试时使用）
# 部署到服务器后请删除以下两行
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#VERIFY_SSL = False  # 服务器上改为 True
VERIFY_SSL = True# 服务器上改为 True

# ── 路径配置 ─────────────────────────────────────────────────────────────────

# 本文件位于 crawlers/ai/，所以博客根目录是上两级
CRAWLER_DIR = os.path.dirname(__file__)                        # crawlers/ai/
BLOG_ROOT   = os.path.dirname(os.path.dirname(CRAWLER_DIR))   # blog/

CONFIG_FILE = os.path.join(CRAWLER_DIR, "ai_config.json")     # crawlers/ai/ai_config.json
POSTS_DIR   = os.path.join(BLOG_ROOT, "posts", "ai")          # posts/ai/
LOG_DIR     = os.path.join(BLOG_ROOT, "logs")                 # logs/

# ── 日志配置 ─────────────────────────────────────────────────────────────────

os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"ai_fetch_news_{datetime.date.today().strftime('%Y-%m-%d')}.log")

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
    """从 ai_config.json 加载配置"""
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"配置文件不存在: {CONFIG_FILE}")
        raise FileNotFoundError(f"找不到配置文件: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info(f"成功加载配置文件，共 {len(config['sources'])} 个来源")
    return config


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def is_ai_related(text: str, lang: str, keywords: dict) -> bool:
    """判断文章是否与 AI 相关"""
    text_lower = text.lower()
    kw_list = keywords.get(lang, keywords.get("en", []))
    return any(kw.lower() in text_lower for kw in kw_list)


def clean_html(text: str) -> str:
    """去除 HTML 标签"""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def truncate(text: str, max_len: int = 150) -> str:
    """截断文本"""
    text = clean_html(text)
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


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

        for entry in feed.entries[:10]:
            title = clean_html(entry.get("title", ""))
            summary = truncate(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")

            logger.debug(f"  检查文章: {title[:60]}")

            if not is_ai_related(title + " " + summary, source["lang"], keywords):
                logger.debug(f"  -> 跳过（非 AI 相关）")
                continue

            logger.debug(f"  -> 收录！")
            articles.append({
                "title": title,
                "summary": summary,
                "link": link,
                "source": source["name"],
                "source_zh": source["name_zh"],
                "lang": source["lang"],
            })

        logger.info(f"完成 {source['name_zh']}: 抓取到 {len(articles)} 条 AI 相关文章")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"网络连接失败 {source['name_zh']}: {e}")
    except requests.exceptions.Timeout:
        logger.error(f"请求超时 {source['name_zh']}")
    except Exception as e:
        logger.error(f"抓取失败 {source['name_zh']}: {type(e).__name__}: {e}")

    return articles


def generate_markdown(articles: list, date: datetime.date) -> str:
    """生成中英双语 Markdown 简报"""
    date_str = date.strftime("%Y-%m-%d")
    date_zh = date.strftime("%Y年%m月%d日")

    en_articles = [a for a in articles if a["lang"] == "en"]
    zh_articles = [a for a in articles if a["lang"] == "zh"]

    lines = [
        f"---",
        f"title: AI 资讯简报 | AI News Digest {date_str}",
        f"date: {date_str}",
        f"tags: [AI, 简报, News Digest]",
        f"summary: {date_zh} AI 领域最新资讯汇总，涵盖国内外重要动态。",
        f"---",
        f"",
        f"# AI 资讯简报 | AI News Digest",
        f"",
        f"> 日期: {date_zh} | 自动抓取自 {len(set(a['source'] for a in articles))} 个来源，共 {len(articles)} 条资讯",
        f"",
        f"---",
        f"",
    ]

    if zh_articles:
        lines += [f"## 国内 AI 资讯", f""]
        for i, article in enumerate(zh_articles, 1):
            lines += [
                f"### {i}. {article['title']}",
                f"",
                f"- **来源**: {article['source_zh']}",
                f"- **链接**: [{article['link']}]({article['link']})",
                f"- **摘要**: {article['summary']}",
                f"",
            ]

    if en_articles:
        lines += [f"## International AI News", f""]
        for i, article in enumerate(en_articles, 1):
            lines += [
                f"### {i}. {article['title']}",
                f"",
                f"- **Source**: {article['source']}",
                f"- **Link**: [{article['link']}]({article['link']})",
                f"- **Summary**: {article['summary']}",
                f"",
            ]

    lines += [
        f"---",
        f"",
        f"*本简报由自动脚本生成 | Auto-generated by ai_fetch_news.py*",
    ]

    return "\n".join(lines)


def save_post(content: str, date: datetime.date) -> str:
    """保存为 Markdown 文件到 posts/ai/"""
    os.makedirs(POSTS_DIR, exist_ok=True)
    date_str = date.strftime("%Y-%m-%d")
    filename = f"{date_str}-ai-news-digest.md"
    filepath = os.path.join(POSTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


# ── 主程序 ───────────────────────────────────────────────────────────────────

def main():
    today = datetime.date.today()
    logger.info("=" * 50)
    logger.info(f"开始抓取 AI 资讯简报 ({today})")
    logger.info(f"文章保存至: {POSTS_DIR}")
    logger.info("=" * 50)

    config = load_config()
    sources = config["sources"]
    keywords = config["keywords"]

    all_articles = []
    for source in sources:
        articles = fetch_feed(source, keywords)
        all_articles.extend(articles)

    logger.info(f"共抓取到 {len(all_articles)} 条 AI 相关资讯")

    if not all_articles:
        logger.warning("没有抓取到任何文章，请检查网络连接或 RSS 地址是否有效")
        logger.info(f"日志已保存至: {log_filename}")
        return

    content = generate_markdown(all_articles, today)
    filename = save_post(content, today)
    logger.info(f"简报已保存：posts/ai/{filename}")
    logger.info(f"日志已保存至: {log_filename}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
