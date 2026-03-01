import os
import re
import json
import hashlib
import secrets
from datetime import datetime
from flask import (Flask, render_template, abort, request, jsonify,
                   session, redirect, url_for, flash)
import markdown
import yaml

app = Flask(__name__)

# 从环境变量读取 secret key，生产环境必须设置 FLASK_SECRET_KEY
# 本地开发时若未设置，自动生成一个临时 key（重启后 session 会失效，属正常现象）
_secret = os.environ.get("FLASK_SECRET_KEY")
if not _secret:
    import warnings
    warnings.warn(
        "未设置环境变量 FLASK_SECRET_KEY，已使用随机临时 key。"
        "生产环境请在 .env 或服务器环境变量中设置该值。",
        stacklevel=1,
    )
    _secret = secrets.token_hex(32)
app.secret_key = _secret

POSTS_DIR = os.path.join(os.path.dirname(__file__), "posts")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


# ── 用户管理 ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        default = {"admin": hash_password("admin123")}
        save_users(default)
        return default
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── 核心：解析 Markdown 文件 ──────────────────────────────────────────────────

def parse_post(filepath: str) -> dict | None:
    """解析单篇文章，支持 posts/ 下任意子目录"""
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    front_matter = {}
    content = raw
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if fm_match:
        try:
            front_matter = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            pass
        content = raw[fm_match.end():]

    # slug 使用相对于 posts/ 的路径，例如 ai/2026-02-26-ai-news-digest
    rel_path = os.path.relpath(filepath, POSTS_DIR)
    slug = rel_path.replace("\\", "/").replace(".md", "")

    # 分类（子目录名称），例如 ai、finance
    parts = slug.split("/")
    category = parts[0] if len(parts) > 1 else "general"

    filename = os.path.basename(filepath)

    date = front_matter.get("date")
    if not date:
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
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

    tags = front_matter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "codehilite", "nl2br"],
        extension_configs={"codehilite": {"linenums": False}},
    )
    html_content = md.convert(content)

    return {
        "slug": slug,
        "category": category,
        "filename": filename,
        "filepath": filepath,
        "title": front_matter.get("title", filename),
        "date": date,
        "date_str": date.strftime("%Y年%m月%d日") if date else "未知日期",
        "tags": tags,
        "summary": front_matter.get("summary", content[:120].strip() + "..."),
        "content": html_content,
        "toc": getattr(md, "toc", ""),
        "raw": raw,
    }


def get_all_posts(category: str = None) -> list:
    """递归扫描 posts/ 及其所有子目录，返回所有文章"""
    if not os.path.exists(POSTS_DIR):
        os.makedirs(POSTS_DIR)
        return []

    posts = []
    for root, dirs, files in os.walk(POSTS_DIR):
        # 忽略隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(root, filename)
            post = parse_post(filepath)
            if post:
                # 如果指定了分类则过滤
                if category and post["category"] != category:
                    continue
                posts.append(post)

    posts.sort(key=lambda p: p["date"] or datetime.min.date(), reverse=True)
    return posts


def get_all_tags(posts: list) -> dict:
    tag_count = {}
    for post in posts:
        for tag in post["tags"]:
            tag_count[tag] = tag_count.get(tag, 0) + 1
    return dict(sorted(tag_count.items(), key=lambda x: x[1], reverse=True))


def get_all_categories() -> dict:
    """获取所有分类及其文章数量"""
    posts = get_all_posts()
    cat_count = {}
    for post in posts:
        cat = post["category"]
        cat_count[cat] = cat_count.get(cat, 0) + 1
    return cat_count


def make_filename(title: str, date: str = None) -> str:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    if not slug:
        slug = "untitled"
    return f"{date}-{slug}.md"


@app.context_processor
def inject_categories():
    return {"all_categories": get_all_categories(), "now":datetime.now()}




CAT_ICONS = {
    "ai":      "🤖",
    "general": "📝",
    "tech":    "💻",
    "finance": "💰",
    "life":    "🌱",
    "travel":  "✈️",
    "book":    "📚",
    "news":    "📰",
}


@app.route("/")
@app.route("/blog")
def index():
    categories = get_all_categories()
    return render_template("categories.html", categories=categories, cat_icons=CAT_ICONS)


@app.route("/blog/posts")
def all_posts():
    posts = get_all_posts()
    tags = get_all_tags(posts)
    categories = get_all_categories()
    return render_template("index.html", posts=posts, tags=tags, categories=categories)


@app.route("/blog/category/<category>")
def category_filter(category: str):
    posts = get_all_posts(category=category)
    tags = get_all_tags(posts)
    categories = get_all_categories()
    return render_template("index.html", posts=posts, tags=tags, categories=categories, active_category=category)


@app.route("/blog/<path:slug>")
def post_detail(slug: str):
    # slug 可能是 ai/2026-02-26-ai-news-digest
    filepath = os.path.join(POSTS_DIR, slug + ".md")
    post = parse_post(filepath)
    if not post:
        abort(404)

    all_posts = get_all_posts()
    slugs = [p["slug"] for p in all_posts]
    idx = slugs.index(slug) if slug in slugs else -1
    prev_post = all_posts[idx + 1] if idx >= 0 and idx + 1 < len(all_posts) else None
    next_post = all_posts[idx - 1] if idx > 0 else None

    return render_template("post.html", post=post, prev_post=prev_post, next_post=next_post)


@app.route("/blog/tag/<tag>")
def tag_filter(tag: str):
    all_posts = get_all_posts()
    posts = [p for p in all_posts if tag in p["tags"]]
    tags = get_all_tags(all_posts)
    categories = get_all_categories()
    return render_template("index.html", posts=posts, tags=tags, categories=categories, active_tag=tag)


@app.route("/blog/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    results = []
    for post in get_all_posts():
        searchable = " ".join([
            post["title"].lower(),
            post["summary"].lower(),
            " ".join(post["tags"]).lower(),
            post["category"].lower(),
        ])
        if q in searchable:
            results.append({
                "slug": post["slug"],
                "title": post["title"],
                "date_str": post["date_str"],
                "summary": post["summary"],
                "tags": post["tags"],
                "category": post["category"],
            })

    return jsonify(results)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def get_client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()


# ── 登录 / 登出 ───────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = load_users()
        if username in users and users[username] == hash_password(password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("admin_index"))
        flash("用户名或密码错误")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── 后台管理路由 ──────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
def admin_index():
    posts = get_all_posts()
    categories = get_all_categories()
    return render_template("admin/index.html", posts=posts, categories=categories)


@app.route("/admin/new", methods=["GET", "POST"])
@login_required
def admin_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        tags = request.form.get("tags", "")
        category = request.form.get("category", "general").strip()

        filename = make_filename(title, date)
        # 保存到对应分类子目录
        category_dir = os.path.join(POSTS_DIR, category)
        os.makedirs(category_dir, exist_ok=True)
        filepath = os.path.join(category_dir, filename)

        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        front_matter = f"---\ntitle: {title}\ndate: {date}\ntags: {tags_list}\n---\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(front_matter + content)

        flash(f"文章已创建：{category}/{filename}")
        return redirect(url_for("admin_index"))

    categories = get_all_categories()
    return render_template("admin/edit.html", post=None, today=datetime.now().strftime("%Y-%m-%d"), categories=categories)


@app.route("/admin/edit/<path:slug>", methods=["GET", "POST"])
@login_required
def admin_edit(slug: str):
    filepath = os.path.join(POSTS_DIR, slug + ".md")

    if not os.path.exists(filepath):
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        flash("文章已保存")
        return redirect(url_for("admin_edit", slug=slug))

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    post = {"slug": slug, "filename": os.path.basename(filepath), "raw": raw}
    return render_template("admin/edit.html", post=post, today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/admin/delete/<path:slug>", methods=["POST"])
@login_required
def admin_delete(slug: str):
    filepath = os.path.join(POSTS_DIR, slug + ".md")
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f"文章 {slug} 已删除")
    return redirect(url_for("admin_index"))


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    file = request.files.get("file")
    category = request.form.get("category", "general").strip()

    if not file or not file.filename.endswith(".md"):
        flash("请上传 .md 文件")
        return redirect(url_for("admin_index"))

    original_name = os.path.splitext(file.filename)[0]
    safe_name = re.sub(r"[^\w\u4e00-\u9fff-]", "-", original_name).strip("-")
    date_prefix = datetime.now().strftime("%Y-%m-%d")

    if re.match(r"^\d{4}-\d{2}-\d{2}", safe_name):
        filename = safe_name + ".md"
    else:
        filename = f"{date_prefix}-{safe_name}.md"

    category_dir = os.path.join(POSTS_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    filepath = os.path.join(category_dir, filename)
    file.save(filepath)
    flash(f"文件已上传：{category}/{filename}")
    return redirect(url_for("admin_index"))


@app.route("/admin/users", methods=["GET", "POST"])
@login_required
def admin_users():
    users = load_users()
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username", "").strip()

        if action == "add" and username:
            password = request.form.get("password", "")
            users[username] = hash_password(password)
            save_users(users)
            flash(f"用户 {username} 已添加")

        elif action == "delete" and username:
            if username == session.get("username"):
                flash("不能删除自己的账户")
            elif username in users:
                del users[username]
                save_users(users)
                flash(f"用户 {username} 已删除")

        return redirect(url_for("admin_users"))

    return render_template("admin/users.html", users=users)


# ── 在线终端 ──────────────────────────────────────────────────────────────────

# 白名单：只允许以下命令前缀
TERMINAL_WHITELIST = [
    "git pull",
    "git status",
    "git log --oneline",
    "systemctl restart blog",
    "systemctl status blog",
    "systemctl stop blog",
    "systemctl start blog",
    "ls",
    "ls -la",
    "cat logs/",
    "cat posts/",
    "pwd",
]

TERMINAL_LOG = os.path.join(os.path.dirname(__file__), "logs", "terminal.log")


def log_terminal_cmd(username: str, ip: str, cmd: str, allowed: bool):
    """记录终端操作日志"""
    os.makedirs(os.path.dirname(TERMINAL_LOG), exist_ok=True)
    status = "ALLOWED" if allowed else "BLOCKED"
    with open(TERMINAL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{status}] user={username} ip={ip} cmd={cmd}\n")


def is_cmd_allowed(cmd: str) -> bool:
    """检查命令是否在白名单中"""
    cmd = cmd.strip()
    for allowed in TERMINAL_WHITELIST:
        if cmd == allowed or cmd.startswith(allowed + " ") or cmd.startswith(allowed + "/"):
            return True
    return False


@app.route("/admin/terminal")
@login_required
def admin_terminal():
    return render_template("admin/terminal.html", whitelist=TERMINAL_WHITELIST)


@app.route("/admin/terminal/exec", methods=["POST"])
@login_required
def terminal_exec():
    import subprocess
    cmd = request.json.get("cmd", "").strip()
    username = session.get("username", "unknown")
    ip = get_client_ip()

    if not cmd:
        return jsonify({"output": ""})

    if not is_cmd_allowed(cmd):
        log_terminal_cmd(username, ip, cmd, allowed=False)
        allowed_list = "\n".join(f"  - {w}" for w in TERMINAL_WHITELIST)
        return jsonify({"output": f"⚠️ 命令不在白名单中，已拒绝：{cmd}\n\n允许的命令：\n{allowed_list}"})

    log_terminal_cmd(username, ip, cmd, allowed=True)

    try:
        env = os.environ.copy()
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=15, cwd=os.path.dirname(__file__),
            env=env
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr
        return jsonify({"output": output if output else f"(无输出，返回码: {result.returncode})"})
    except subprocess.TimeoutExpired:
        return jsonify({"output": "⚠️ 命令执行超时（15秒）"})
    except Exception as e:
        return jsonify({"output": f"错误：{type(e).__name__}: {str(e)}"})


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
