# 网站更新指南

## 快速更新步骤

### 1. 本地修改代码
```bash
# 在本地进行修改
# ...

# 提交更改
git add .
git commit -m "描述你的更改"
git push origin main
```

### 2. 服务器更新
```bash
# SSH 登录到服务器
ssh user@your-server-ip

# 进入项目目录
cd /home/echo/blog

# 拉取最新代码
git pull origin main

# 更新依赖（如有需要）
source venv/bin/activate
pip install -r requirements.txt

# 同步数据库
python sync_db.py

# 重启服务
sudo systemctl restart blog
```

### 3. 验证更新
```bash
# 检查服务状态
sudo systemctl status blog

# 查看日志
sudo tail -f /var/log/blog/error.log

# 访问网站测试
curl http://your-domain.com
```

---

## 爬虫数据同步

### 工作流程
```
定时任务 → 爬虫抓取 → 生成MD文件 → 自动同步数据库
```

### 爬虫自动同步
爬虫脚本已配置为运行后自动同步数据库：

```bash
# 爬虫运行脚本
bash crawlers/run.sh all
# 会自动执行数据库同步
```

### 手动同步
```bash
# 快速同步
python sync_db.py

# 完整迁移（包含表创建）
python migrate_to_db.py
```

---

## 更新文件清单

需要更新的文件：
- `app.py` - Flask 应用
- `models.py` - 数据库模型
- `database.py` - 数据库管理
- `sync_db.py` - 快速同步脚本
- `migrate_to_db.py` - 完整迁移脚本
- `crawlers/run.sh` - 爬虫运行脚本（已更新）
- `static/css/style.css` - 样式文件
- `static/js/*.js` - JavaScript文件
- `templates/*.html` - 模板文件
- `templates/admin/*.html` - 管理后台模板

---

## 常见问题

### Q: 爬虫数据需要手动同步吗？
A: 不需要。爬虫脚本已配置为运行后自动同步数据库。

### Q: 如何查看数据库同步状态？
A:
```bash
# 查看数据库统计
python -c "
from app import app
from models import db, Post, Tag, ViewLog
with app.app_context():
    print(f'文章: {Post.query.count()}')
    print(f'标签: {Tag.query.count()}')
    print(f'阅读记录: {ViewLog.query.count()}')
"
```

### Q: 数据库文件在哪里？
A: `/home/echo/blog/blog.db`

### Q: 如何备份数据库？
A:
```bash
# 手动备份
cp /home/echo/blog/blog.db /var/backups/blog_$(date +%Y%m%d).db

# 定时任务已配置每周自动备份
```

### Q: 更新后服务无法启动？
A:
```bash
# 查看详细错误
sudo journalctl -u blog -n 50

# 检查数据库
ls -la blog.db

# 重新同步数据库
python sync_db.py

# 重启服务
sudo systemctl restart blog
```

---

## 数据库同步说明

### 同步逻辑
1. **新文章** - 从 MD 文件创建数据库记录
2. **更新文章** - 更新现有文章的内容和元数据
3. **标签管理** - 自动创建和关联标签
4. **搜索索引** - 更新全文搜索索引

### 保留的功能
- Markdown 文件仍然是主要存储方式
- 数据库用于统计、搜索、缓存
- 文件系统和数据库保持同步

---

## 监控和日志

### 查看爬虫日志
```bash
# 查看最新爬虫日志
tail -f /var/log/blog/crawler.log
```

### 查看数据库同步日志
```bash
# 爬虫运行时的输出会显示同步过程
bash crawlers/run.sh all
```

### 检查数据库完整性
```bash
python -c "
from app import app, POSTS_DIR
from database import get_posts_from_db
import os

with app.app_context():
    db_posts = len(get_posts_from_db())
    md_files = len([f for f in os.listdir(POSTS_DIR) if f.endswith('.md')])
    print(f'数据库文章: {db_posts}')
    print(f'MD文件数量: {md_files}')
    print(f'状态: {'同步' if db_posts == md_files else '需要同步'}')
"
```

---

## 自动化更新脚本

创建 `update.sh` 自动更新脚本：

```bash
#!/bin/bash
set -e

echo "=== 网站更新脚本 ==="

cd /home/echo/blog

# 1. 拉取最新代码
echo "1. 拉取最新代码..."
git pull origin main

# 2. 激活虚拟环境
echo "2. 激活虚拟环境..."
source venv/bin/activate

# 3. 更新依赖
echo "3. 更新依赖..."
pip install -r requirements.txt

# 4. 同步数据库
echo "4. 同步数据库..."
python sync_db.py

# 5. 重启服务
echo "5. 重启服务..."
sudo systemctl restart blog

echo "=== 更新完成！==="

# 6. 检查状态
echo "检查服务状态..."
sudo systemctl status blog --no-pager
```

使用方法：
```bash
chmod +x update.sh
./update.sh
```

---

## 回滚方案

如果更新后出现问题，可以快速回滚：

```bash
# 回退到上一个版本
cd /home/echo/blog
git log --oneline -5
git reset --hard HEAD~1

# 重启服务
sudo systemctl restart blog

# 或者恢复特定版本
git reset --hard <commit-hash>
```

---

## 性能优化建议

### 数据库优化
```bash
# 定期清理阅读日志（保留最近30天）
python -c "
from app import app
from models import db, ViewLog
from datetime import datetime, timedelta
with app.app_context():
    cutoff = datetime.utcnow() - timedelta(days=30)
    deleted = ViewLog.query.filter(ViewLog.viewed_at < cutoff).delete()
    db.session.commit()
    print(f'删除 {deleted} 条旧记录')
"
```

### 添加到定时任务
```bash
# 编辑 crontab
sudo crontab -e

# 添加：每月1号清理旧日志
0 2 1 * * cd /home/echo/blog && source venv/bin/activate && python -c "from app import app; from models import db, ViewLog; from datetime import datetime, timedelta; app.app_context().push(); deleted = ViewLog.query.filter(ViewLog.viewed_at < datetime.utcnow() - timedelta(days=30)).delete(); db.session.commit(); print(f'删除 {deleted} 条旧记录')" >> /var/log/blog/cleanup.log 2>&1
```

---

如有问题，请检查日志文件或联系技术支持。
