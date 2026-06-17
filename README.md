# 档案政策监控与知识库平台

> 面向医院档案管理人员的智能政策监控与知识管理平台

基于 Flask + SQLite + Scrapling 构建，自动监控国家档案局、卫健委等官方渠道的政策法规更新，智能提取正文内容，并提供全文搜索、知识库管理、Excel 导出等功能。

---

## 🚀 一键启动（推荐新手）

**无需任何命令行操作，双击即可运行！**

1. 进入项目目录，双击运行 `start.bat`
2. 首次运行会自动下载并安装 Python 环境（约 3~5 分钟，只需一次）
3. 安装完成后自动启动服务器，并弹出浏览器
4. 访问地址：
   - 前台首页：`http://127.0.0.1:5050`
   - 管理后台：`http://127.0.0.1:5050/admin`（无需登录，直接进入）

> 💡 如果端口 5050 已被占用，可修改 `config.py` 中的 `PORT` 配置。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [数据源配置](#数据源配置)
- [API 接口](#api-接口)
- [定时任务](#定时任务)
- [常见问题](#常见问题)

---

## 功能特性

### 政策监控
- **多源采集**：支持网页抓取、RSS 订阅等多种数据源
- **智能提取**：无需配置 CSS 选择器，自动识别页面内容列表
- **全文抓取**：自动抓取政策详情页完整正文内容
- **去重机制**：基于 SHA256 哈希自动去重，避免重复收录
- **三级抓取策略**：Scrapling（TLS 指纹伪装）→ requests 降级 → 链接兜底

### 知识管理
- **分类体系**：支持多级分类管理，父分类自动统计子分类条目数
- **智能归类**：基于关键词权重匹配，自动推荐最合适的分类
- **全文搜索**：基于 SQLite FTS5 的全文索引，支持标题/正文/标签联合搜索
- **富文本编辑**：集成 Summernote 编辑器，支持图文混排

### 批量操作
- **批量选择**：表格行内复选框，支持全选/反选
- **批量修改**：批量修改分类、标签、标题（支持查找替换）
- **批量转入**：政策条目一键批量转入知识库，自动智能归类
- **批量删除**：二次确认，防止误删

### 数据管理
- **Excel 导出**：按日期范围、分类、关键词筛选后导出 Excel
- **数据备份**：一键下载数据库备份文件（带时间戳）
- **数据恢复**：上传 `.db` 文件安全恢复，恢复前自动备份原库
- **关键词订阅**：设置关注关键词，新政策命中时自动通知

### 其他
- **无登录限制**：直接访问后台，无需账号登录
- **响应式界面**：基于 Bootstrap 5，适配桌面和移动端
- **深色主题**：深蓝 + 金色配色，专业稳重

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.x + SQLAlchemy + APScheduler |
| 数据库 | SQLite 3（含 FTS5 全文索引） |
| 爬虫 | Scrapling + requests + BeautifulSoup4 |
| 前端 | Bootstrap 5 + jQuery + Summernote + DataTables |
| 导出 | openpyxl（Excel 导出） |

---

## 快速开始

### 环境要求
- Python 3.10+
- pip

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/dalihaif/archive-kb.git
cd archive-kb

# 2. 创建虚拟环境（推荐）
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库并启动
python app.py
```

启动后访问：
- **前台**：http://127.0.0.1:5050/
- **后台**：http://127.0.0.1:5050/admin/

---

## 使用指南

### 首次使用

1. 访问后台 → **管理监控源**，确认预置的 5 个数据源已启用
2. 点击 **立即全量抓取**，等待抓取完成
3. 抓取完成后，在 **政策条目管理** 中查看已收录的政策

### 添加新数据源

1. 后台 → **管理监控源** → **新增数据源**
2. 填写名称和 URL
3. 如需精确抓取，可配置 CSS 选择器（JSON 格式）：
   ```json
   {
     "container": ".news-list li",
     "title": "a",
     "date": ".date",
     "link": "a"
   }
   ```
4. 若不配置选择器，系统会自动智能识别内容列表

### 关键词订阅

1. 后台仪表盘 → **关键词订阅** 面板
2. 输入关注关键词（逗号分隔），如：`电子病历,病案管理,归档,数字化`
3. 点击保存
4. 新政策标题命中关键词时，导航栏会显示红点通知

### Excel 导出

- 后台仪表盘点击 **导出 Excel**
- 或政策管理页点击 **导出** 按钮
- 可按日期范围筛选导出

---

## 项目结构

```
archive-kb/
├── app.py                  # 应用入口，Flask 初始化
├── models.py              # 数据库模型（5张核心表 + FTS5初始化）
├── crawler.py              # 爬虫引擎（三级策略 + 智能提取 + 全文抓取）
├── requirements.txt        # Python 依赖
├── config.py              # 配置文件（可选）
├── instance/
│   └── archive.db         # SQLite 数据库（自动创建）
├── routes/
│   ├── __init__.py
│   ├── admin.py            # 后台管理路由（20+ API 端点）
│   └── main.py             # 前台展示路由（含 FTS5 搜索）
├── templates/
│   ├── base.html           # 基础模板（含导航栏通知红点）
│   ├── index.html          # 前台首页
│   ├── knowledge.html      # 前台知识库浏览
│   ├── policy_detail.html  # 政策详情页
│   └── admin/
│       ├── dashboard.html  # 后台仪表盘（含关键词订阅面板）
│       ├── sources.html    # 数据源管理
│       ├── policies.html   # 政策条目管理（含批量操作）
│       ├── knowledge.html  # 知识库管理（含批量编辑）
│       ├── categories.html # 分类体系管理
│       └── login.html      # 登录页（已自动跳转，无需使用）
└── static/
    ├── css/
    ├── js/
    └── uploads/
```

---

## 数据源配置

预置数据源（首次启动自动创建）：

| 名称 | URL | 分类 |
|------|-----|------|
| 国家档案局 - 政策法规 | https://www.saac.gov.cn/ | 档案局 |
| 国家卫健委 - 政策文件 | https://www.gov.cn/fuwu/bm/wjw/index.htm | 卫健委 |
| 国家法律法规数据库 | https://flk.npc.gov.cn/ | 法律法规 |
| 中国政府网 - 政策 | https://www.gov.cn/zhengce/ | 法律法规 |
| 中国医院协会 - 行业动态 | https://www.cha.org.cn/ | 行业动态 |

> **注意**：国家卫健委官网（nhc.gov.cn）有 WAF 保护，已改用 gov.cn 替代入口。

---

## API 接口

### 政策相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/policies` | 政策列表（支持 q/category/date 筛选） |
| GET | `/api/policies/<id>` | 获取单条政策详情 |
| PUT | `/api/policies/<id>` | 更新政策 |
| DELETE | `/api/policies/<id>` | 删除政策 |
| PUT | `/api/policies/batch` | 批量修改政策 |
| GET | `/api/policies/export` | 导出 Excel（支持 date_from/date_to/category/q） |

### 知识库相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge` | 知识库列表 |
| GET | `/api/knowledge/<id>` | 获取单条知识条目 |
| POST | `/api/knowledge` | 新建知识条目 |
| PUT | `/api/knowledge/<id>` | 更新知识条目 |
| DELETE | `/api/knowledge/<id>` | 删除知识条目 |
| PUT | `/api/knowledge/batch` | 批量修改 |
| POST | `/api/knowledge/batch-suggest` | 批量智能分类建议 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/api/stats` | 仪表盘统计数据 |
| GET | `/admin/api/backup` | 下载数据库备份 |
| POST | `/admin/api/restore` | 上传恢复数据库 |
| GET | `/admin/api/alerts/keywords` | 获取订阅关键词 |
| PUT | `/admin/api/alerts/keywords` | 更新订阅关键词 |
| GET | `/admin/api/alerts/check` | 检查新政策命中通知 |

---

## 定时任务

项目使用 APScheduler 实现定时抓取（需在 `app.py` 中启用）：

```python
# 每天上午 9:00 自动抓取
scheduler.add_job(
    func=crawl_all_job,
    trigger='cron',
    hour=9,
    minute=0,
    id='daily_crawl'
)
```

也可通过 Windows 任务计划程序或 Linux crontab 调用：
```bash
# 每天 9:00 触发抓取
0 9 * * * curl -X POST http://127.0.0.1:5050/admin/api/crawl-all
```

---

## 数据库 schema

### 核心表

- **users** - 管理员用户（含 alert_keywords 订阅字段）
- **monitor_sources** - 监控数据源配置
- **policies** - 政策条目（含 content 正文、FTS5 索引）
- **categories** - 知识分类体系（支持多级）
- **knowledge_items** - 知识库条目
- **monitor_logs** - 抓取日志

### FTS5 全文索引

- **policies_fts** - 政策全文索引（title/content/summary/tags）
- **knowledge_fts** - 知识库全文索引（title/content/tags）

索引通过 SQLite 触发器自动与主表保持同步。

---

## 常见问题

### Q: 抓取失败/返回空数据？
A: 政府网站常有 WAF 保护，尝试：
1. 检查数据源 URL 是否可访问
2. 换用 RSS 源（若有）
3. 手动配置 CSS 选择器

### Q: 全文搜索不生效？
A: 检查 FTS5 索引是否初始化：访问后台，若提示 FTS5 错误，删除 `instance/archive.db` 重新启动。

### Q: 如何迁移到其他机器？
A: 直接复制整个项目目录，或导出数据库备份后在目标机器恢复。

### Q: 端口被占用？
A: 修改 `app.py` 中的 `port=5050` 为其他端口。

---

## 开源协议

MIT License

---

## 致谢

- [Scrapling](https://github.com/D4Vinci/Scrapling) - 强大的 Python 爬虫框架
- [Flask](https://flask.palletsprojects.com/) - 轻量级 Web 框架
- [Bootstrap](https://getbootstrap.com/) - 前端 UI 框架
- [Summernote](https://summernote.org/) - WYSIWYG 富文本编辑器

---

*最后更新：2026-06-18*
