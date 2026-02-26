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
#app.secret_key = secrets.token_hex(32)  # 每次重启会变，如需持久化请替换为固定字符串
app.secret_key = "f5eaeae85879177c50793d04a06808c428d7c661e43c88459297551f182b6712"

POSTS_DIR = os.path.join(os.path.dirname(__file__), "posts")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


# ─────────────────────────────────────────
# 用户管理
# ─────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        # 默认创建 admin 账户，密码 admin123
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


# ─────────────────────────────────────────
# 核心：解析 Markdown 文件
# ─────────────────────────────────────────

def parse_post(filename: str) -> dict | None:
    filepath = os.path.join(POSTS_DIR, filename)
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

    slug = filename[:-3]

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
        "filename": filename,
        "title": front_matter.get("title", slug),
        "date": date,
        "date_str": date.strftime("%Y年%m月%d日") if date else "未知日期",
        "tags": tags,
        "summary": front_matter.get("summary", content[:120].strip() + "…"),
        "content": html_content,
        "toc": getattr(md, "toc", ""),
        "raw": raw,
    }


def get_all_posts() -> list[dict]:
    if not os.path.exists(POSTS_DIR):
        os.makedirs(POSTS_DIR)
        return []

    posts = []
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            post = parse_post(filename)
            if post:
                posts.append(post)

    posts.sort(key=lambda p: p["date"] or datetime.min.date(), reverse=True)
    return posts


def get_all_tags(posts: list[dict]) -> dict:
    tag_count = {}
    for post in posts:
        for tag in post["tags"]:
            tag_count[tag] = tag_count.get(tag, 0) + 1
    return dict(sorted(tag_count.items(), key=lambda x: x[1], reverse=True))


def make_filename(title: str, date: str = None) -> str:
    """根据标题和日期生成安全的文件名"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    # 将标题转为 slug（移除特殊字符，空格换成横线）
    slug = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    if not slug:
        slug = "untitled"
    return f"{date}-{slug}.md"


# ─────────────────────────────────────────
# 公开路由
# ─────────────────────────────────────────

@app.route("/")
@app.route("/blog")
def index():
    posts = get_all_posts()
    tags = get_all_tags(posts)
    return render_template("index.html", posts=posts, tags=tags)


@app.route("/blog/<slug>")
def post_detail(slug: str):
    filename = slug + ".md"
    post = parse_post(filename)
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
    return render_template("index.html", posts=posts, tags=tags, active_tag=tag)


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


# ─────────────────────────────────────────
# 登录 / 登出
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# 后台管理路由
# ─────────────────────────────────────────

@app.route("/admin")
@login_required
def admin_index():
    posts = get_all_posts()
    return render_template("admin/index.html", posts=posts)


@app.route("/admin/new", methods=["GET", "POST"])
@login_required
def admin_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        tags = request.form.get("tags", "")

        filename = make_filename(title, date)
        filepath = os.path.join(POSTS_DIR, filename)

        # 构建 Front Matter
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        front_matter = f"---\ntitle: {title}\ndate: {date}\ntags: {tags_list}\n---\n\n"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(front_matter + content)

        flash(f"文章已创建：{filename}")
        return redirect(url_for("admin_index"))

    return render_template("admin/edit.html", post=None, today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/admin/edit/<slug>", methods=["GET", "POST"])
@login_required
def admin_edit(slug: str):
    filename = slug + ".md"
    filepath = os.path.join(POSTS_DIR, filename)

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

    post = {"slug": slug, "filename": filename, "raw": raw}
    return render_template("admin/edit.html", post=post, today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/admin/delete/<slug>", methods=["POST"])
@login_required
def admin_delete(slug: str):
    filename = slug + ".md"
    filepath = os.path.join(POSTS_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f"文章 {filename} 已删除")
    return redirect(url_for("admin_index"))


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".md"):
        flash("请上传 .md 文件")
        return redirect(url_for("admin_index"))

    # 自动生成文件名：日期前缀 + 原文件名
    original_name = os.path.splitext(file.filename)[0]
    safe_name = re.sub(r"[^\w\u4e00-\u9fff-]", "-", original_name).strip("-")
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    
    # 如果文件名已经有日期前缀则不重复添加
    if re.match(r"^\d{4}-\d{2}-\d{2}", safe_name):
        filename = safe_name + ".md"
    else:
        filename = f"{date_prefix}-{safe_name}.md"

    filepath = os.path.join(POSTS_DIR, filename)
    file.save(filepath)
    flash(f"文件已上传：{filename}")
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


# ─────────────────────────────────────────
# 网页终端（WebSocket-free 轮询方式）
# ─────────────────────────────────────────

@app.route("/admin/terminal")
@login_required
def admin_terminal():
    return render_template("admin/terminal.html")


@app.route("/admin/terminal/exec", methods=["POST"])
@login_required
def terminal_exec():
    import subprocess
    cmd = request.json.get("cmd", "").strip()
    if not cmd:
        return jsonify({"output": ""})

    BLOCKED = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for b in BLOCKED:
        if b in cmd:
            return jsonify({"output": f"⚠️ 命令被阻止：{b}"})

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=15, cwd=os.path.dirname(__file__),
            env=os.environ.copy()
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr
        return jsonify({"output": output if output else "(无输出，返回码: " + str(result.returncode) + ")"})
    except subprocess.TimeoutExpired:
        return jsonify({"output": "⚠️ 命令执行超时（15秒）"})
    except Exception as e:
        return jsonify({"output": f"错误：{type(e).__name__}: {str(e)}"})


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
