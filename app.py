import os
import re
from datetime import datetime
from functools import lru_cache
from flask import Flask, render_template, abort, request, jsonify
import markdown
import yaml

app = Flask(__name__)

POSTS_DIR = os.path.join(os.path.dirname(__file__), "posts")


# ─────────────────────────────────────────
# 核心：解析 Markdown 文件
# ─────────────────────────────────────────

def parse_post(filename: str) -> dict | None:
    """读取并解析单篇博客（含 Front Matter）"""
    filepath = os.path.join(POSTS_DIR, filename)
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # 解析 Front Matter（--- 包裹的 YAML）
    front_matter = {}
    content = raw
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if fm_match:
        try:
            front_matter = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            pass
        content = raw[fm_match.end():]

    # slug = 文件名去掉 .md
    slug = filename[:-3]

    # 日期：优先取 front matter，其次从文件名前缀解析
    date = front_matter.get("date")
    if not date:
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
        if date_match:
            try:
                date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                date = None
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            date = None

    # 标签统一转为列表
    tags = front_matter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    # Markdown → HTML（支持代码高亮、表格、TOC）
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "codehilite", "nl2br"],
        extension_configs={"codehilite": {"linenums": False}},
    )
    html_content = md.convert(content)

    return {
        "slug": slug,
        "title": front_matter.get("title", slug),
        "date": date,
        "date_str": date.strftime("%Y年%m月%d日") if date else "未知日期",
        "tags": tags,
        "summary": front_matter.get("summary", content[:120].strip() + "…"),
        "content": html_content,
        "toc": getattr(md, "toc", ""),
    }


def get_all_posts() -> list[dict]:
    """读取所有博客，按日期倒序排列"""
    if not os.path.exists(POSTS_DIR):
        return []

    posts = []
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            post = parse_post(filename)
            if post:
                posts.append(post)

    # 日期倒序，没有日期的排最后
    posts.sort(key=lambda p: p["date"] or datetime.min.date(), reverse=True)
    return posts


def get_all_tags(posts: list[dict]) -> dict:
    """统计所有标签及其文章数量"""
    tag_count = {}
    for post in posts:
        for tag in post["tags"]:
            tag_count[tag] = tag_count.get(tag, 0) + 1
    return dict(sorted(tag_count.items(), key=lambda x: x[1], reverse=True))


# ─────────────────────────────────────────
# 路由
# ─────────────────────────────────────────

@app.route("/")
@app.route("/blog")
def index():
    """文章列表页"""
    posts = get_all_posts()
    tags = get_all_tags(posts)
    return render_template("index.html", posts=posts, tags=tags)


@app.route("/blog/<slug>")
def post_detail(slug: str):
    """文章详情页"""
    filename = slug + ".md"
    post = parse_post(filename)
    if not post:
        abort(404)

    # 上一篇 / 下一篇
    all_posts = get_all_posts()
    slugs = [p["slug"] for p in all_posts]
    idx = slugs.index(slug) if slug in slugs else -1
    prev_post = all_posts[idx + 1] if idx >= 0 and idx + 1 < len(all_posts) else None
    next_post = all_posts[idx - 1] if idx > 0 else None

    return render_template("post.html", post=post, prev_post=prev_post, next_post=next_post)


@app.route("/blog/tag/<tag>")
def tag_filter(tag: str):
    """标签筛选页"""
    all_posts = get_all_posts()
    posts = [p for p in all_posts if tag in p["tags"]]
    tags = get_all_tags(all_posts)
    return render_template("index.html", posts=posts, tags=tags, active_tag=tag)


@app.route("/blog/search")
def search():
    """搜索接口（返回 JSON，前端 JS 调用）"""
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    results = []
    for post in get_all_posts():
        # 在标题、摘要、标签中搜索
        searchable = " ".join([
            post["title"].lower(),
            post["summary"].lower(),
            " ".join(post["tags"]).lower(),
        ])
        if q in searchable:
            results.append({
                "slug": post["slug"],
                "title": post["title"],
                "date_str": post["date_str"],
                "summary": post["summary"],
                "tags": post["tags"],
            })

    return jsonify(results)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ─────────────────────────────────────────
# 启动
# ─────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
