---
name: think-tank-builder
description: |
  智库搜集平台快速搭建指南。从零搭建一个完整的"内容监控+知识库管理"平台，
  支持多数据源爬取、智能分类、批量编辑、定时调度。适用于政策法规监控、
  行业动态追踪、学术文献管理、竞品情报收集等场景。
  Trigger keywords: 智库, 政策监控, 知识库, 爬虫平台, 内容采集, 情报收集,
  搭建监控, 文献管理, 信息聚合, archive-kb, think tank, knowledge base
---

# 智库搜集平台搭建指南

从零搭建一个完整的"内容监控 + 知识库管理"平台。参考项目：[archive-kb](https://github.com/dalihaif/archive-kb)。

---

## 平台架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Bootstrap 5)                       │
│  首页仪表盘 │ 内容列表 │ 知识库 │ 后台管理                       │
├─────────────────────────────────────────────────────────────┤
│                    Flask Blueprint 路由层                     │
│  前台 (routes/main.py)  │  后台 (routes/admin.py)              │
├─────────────────────────────────────────────────────────────┤
│                  业务层                                        │
│  crawler.py (爬取) │ scheduler.py (调度) │ admin.py (管理)      │
├─────────────────────────────────────────────────────────────┤
│            SQLAlchemy ORM → SQLite / PostgreSQL               │
│   MonitorSource / Policy / Category / KnowledgeItem / User   │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、项目初始化

### 1.1 目录结构

```
project-name/
├── app.py                 # 入口：create_app() + 蓝图注册
├── config.py              # 配置：密钥、数据库URI、调度间隔
├── models.py              # 5张核心表
├── crawler.py             # 爬虫引擎（三级抓取 + 智能提取）
├── scheduler.py           # APScheduler 定时任务
├── requirements.txt       # 依赖
├── routes/
│   ├── __init__.py
│   ├── main.py            # 前台：首页/列表/详情/搜索
│   └── admin.py           # 后台：CRUD API + 批量操作 + 智能归类
├── templates/
│   ├── base.html          # 基础布局（导航 + 底部 + CDN资源）
│   ├── index.html         # 仪表盘首页
│   ├── admin/
│   │   ├── login.html     # 登录页
│   │   ├── dashboard.html
│   │   ├── sources.html   # 数据源CRUD
│   │   ├── policies.html  # 内容条目管理（含批量操作）
│   │   ├── categories.html
│   │   └── knowledge.html # 知识库管理（含Summernote编辑器）
│   └── ...
├── static/
│   ├── css/style.css
│   └── js/main.js
└── instance/              # SQLite 数据库文件目录 (.gitignore)
```

### 1.2 依赖（requirements.txt）

```
flask>=3.1.1
flask-sqlalchemy>=3.1
sqlalchemy>=2.0
beautifulsoup4>=4.12
lxml>=5.0
requests>=2.32.4
apscheduler>=3.10
scrapling[all]>=0.4.9
```

### 1.3 配色方案

全局使用深蓝 + 金色的学术风格配色：
- 主色 `#1A2A4A`（深蓝）- 导航栏、按钮、链接
- 金色 `#D4A84B` - 高亮、激活态、强调元素

---

## 二、数据库模型（5张核心表）

### MonitorSource — 监控数据源

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| name | String(200) | 数据源名称 |
| url | String(500) | 目标URL |
| source_type | String(50) | web / rss / api |
| category | String(100) | 分类标签 |
| crawl_method | String(20) | get / fetch / stealthy |
| selectors | Text | CSS选择器JSON配置 |
| enabled | Boolean | 是否启用 |
| last_crawl_at | DateTime | 最后爬取时间 |
| last_crawl_status | String(20) | success / error |

### Policy — 采集内容条目（核心表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| source_id | FK→MonitorSource | 来源 |
| title | String(500) | 标题（必填） |
| url | String(1000) | 原始链接 |
| summary | Text | 摘要 |
| content | Text | 正文HTML |
| pub_date | Date | 发布日期 |
| authority | String(200) | 发布机构 |
| file_type | String(50) | 文件类型 |
| tags | String(500) | 逗号分隔标签 |
| content_hash | String(64) | **SHA256去重键** |
| is_pinned | Boolean | 置顶 |
| view_count | Integer | 浏览计数 |

**关键索引**：`content_hash`（去重）、`pub_date`（时间排序）、`source_id`（按源查询）。

### Category — 知识库分类（支持二级）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| name | String(200) | 分类名（含分隔符如"档案法规 > 国家法律"） |
| parent_id | FK→self | 自引用外键 |
| sort_order | Integer | |
| icon | String(50) | Bootstrap Icons 类名 |
| description | String(500) | |

**关系**：`parent = relationship('Category', remote_side=[id], backref='children')`

### KnowledgeItem — 知识库条目

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| category_id | FK→Category | |
| title | String(500) | |
| content | Text | Summernote HTML内容 |
| source | String(500) | |
| source_url | String(1000) | |
| tags | String(500) | |
| is_pinned | Boolean | |

### User — 管理员

```python
class User(db.Model):
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(50), unique=True)
    password_hash = db.Column(String(200))  # SHA256 哈希
    is_active = db.Column(Boolean, default=True)
```

**注意**：初始化时自动创建 `admin / admin123` 账户。

---

## 三、爬虫引擎（crawler.py）

### 三级抓取策略

```
1. Scrapling Fetcher (优先)
   ├─ 成功 → 返回 HTML
   └─ 失败 → 降级
2. requests (降级)
   ├─ 成功 → 返回 HTML
   └─ 失败 → 返回 None
```

### 重要：Scrapling 用法

```python
from scrapling import Fetcher
fetcher = Fetcher()  # 不要传 auto_rotate 参数（已废弃）
headers = {
    'User-Agent': 'Mozilla/5.0 ... Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,...',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
page = fetcher.get(url, impersonate='chrome', timeout=30, headers=headers)
html = page.body.decode('utf-8', errors='replace')
```

### 智能内容提取（三级策略）

```
策略1: 用户配置的CSS选择器（selectors字段JSON）
   ↓ 未配置或无结果
策略2: 列表启发式 → 分析所有 <ul>/<ol>，找含链接最多的列表
   ├─ 过滤条件: 链接文本平均长度 ≥ 12字符
   ├─ 去重: seen_titles set
   └─ 智能日期提取
   ↓ 无合适列表
策略3: 兜底 → 提取所有 <a href> 标签
   ├─ 排除导航链接（首页/登录/更多/English...）
   └─ 排除纯数字/日期文本
```

### 去重机制

```python
content_text = f"{title}{content}"
content_hash = hashlib.sha256(content_text.encode()).hexdigest()
existing = Policy.query.filter_by(content_hash=content_hash).first()
if existing:
    continue  # 跳过已存在
```

### 注意事项

- **WAF 保护**：某些政府网站（如 nhc.gov.cn）有 WAF，需换用替代 URL（如 gov.cn 入口）
- **HTTP 412**：添加完整请求头（Accept/Language/Encoding）
- **编码处理**：优先使用 `page.body` 自带的编码信息，备选 `apparent_encoding`
- **预置数据源**：`seed_default_sources()` 在 app 启动时自动填充

---

## 四、路由设计要点

### 4.1 前台路由（routes/main.py）

| 端点 | 功能 | 关键逻辑 |
|------|------|----------|
| `GET /` | 仪表盘首页 | 统计卡片 + 最近内容 |
| `GET /policies` | 内容列表 | 分页 + 分类过滤 + 关键词搜索 |
| `GET /policies/<id>` | 内容详情 | view_count +1, is_read=True |
| `GET /knowledge` | 知识库 | **父分类计数包含子分类** |
| `GET /knowledge/<id>` | 知识条目详情 | view_count +1 |

### 4.2 管理后台路由（routes/admin.py）

完整的 RESTful API 设计：

| 端点 | GET | POST | PUT | DELETE |
|------|-----|------|-----|--------|
| `/api/sources` | - | 创建 | - | - |
| `/api/sources/<id>` | - | - | 更新 | 删除 |
| `/api/sources/<id>/crawl` | - | 触发抓取 | - | - |
| `/api/policies/<id>` | **获取详情** | - | 更新 | **删除** |
| `/api/policies/batch` | - | - | **批量修改** | - |
| `/api/policies/batch-delete` | - | **批量删除** | - | - |
| `/api/policies/batch-to-knowledge` | - | 批量转入 | - | - |
| `/api/policies/batch-suggest` | - | 智能建议 | - | - |
| `/api/knowledge` | - | 创建 | - | - |
| `/api/knowledge/<id>` | **获取详情** | - | 更新 | **删除** |
| `/api/knowledge/batch` | - | - | 批量修改 | - |
| `/api/knowledge/batch-suggest` | - | 智能建议 | - | - |
| `/api/categories` | - | 创建 | - | - |
| `/api/categories/<id>` | - | - | 更新 | **删除** |
| `/api/crawl-all` | - | 全量抓取 | - | - |
| `/api/stats` | 统计数据 | - | - | - |

### 4.3 智能分类建议引擎

核心是 `CATEGORY_KEYWORDS` 字典 + `suggest_category()` 函数：

```python
CATEGORY_KEYWORDS = {
    '档案': [(1, 10), (2, 8)],
    '法规': [(1, 15), (2, 12)],
    '标准': [(3, 15), (4, 10)],
    '卫健委': [(6, 20)],
    '医院': [(6, 12), (5, 8)],
    '数字化': [(9, 15), (5, 8)],
    '保管': [(10, 15)],
    '编目': [(8, 15)],
    # ... 按领域定制
}

def suggest_category(title, source_category=''):
    scores = {}
    for keyword, weighted_cats in CATEGORY_KEYWORDS.items():
        if keyword in title:
            for cat_id, weight in weighted_cats:
                scores[cat_id] = scores.get(cat_id, 0) + weight
    # 按分数降序排序
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**经验法则**：关键词→分类的权重映射是智能归类的核心，需根据实际领域精心设计。

### 4.4 登录认证

使用 session 认证，所有管理路由用 `@login_required` 装饰器保护：

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated
```

---

## 五、前端关键模式

### 5.1 基础模板（base.html）

使用 CDN 加载：
- Bootstrap 5.3.3 CSS + JS
- Bootstrap Icons 1.11.3
- jQuery 3.7.1
- Summernote 0.9.1 (富文本编辑器)

### 5.2 批量操作模式（重要！）

**核心原则**：复选框使用内联 `onchange` 属性而非事件委托。

错误示例：
```javascript
// ❌ 不可靠：事件委托可能不触发
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('item-check')) updateBtns();
});
```

正确示例：
```html
<!-- ✅ 每个复选框直接绑定 onchange -->
<input type="checkbox" class="item-check" value="{{ item.id }}" onchange="updateBtns()">
```

**批量操作栏的实现逻辑**：
```javascript
function updateBtns() {
    var checked = document.querySelectorAll('.item-check:checked');
    var count = checked.length;
    document.getElementById('batchBar').style.display = count > 0 ? '' : 'none';
    document.getElementById('selectedCount').textContent = count;
    // 联动禁用批量按钮
    document.getElementById('btnBatchEdit').disabled = (count === 0);
    document.getElementById('btnBatchDelete').disabled = (count === 0);
}
```

**全选/取消全选**：
```html
<input type="checkbox" id="checkAll" onchange="
    var all = document.querySelectorAll('.item-check');
    all.forEach(function(cb) { cb.checked = this.checked; });
    updateBtns();
">
```

### 5.3 Summernote 编辑器（关键陷阱！）

**陷阱1 — 设置内容**：不能用 `.value`，必须用 `.summernote('code', html)`：
```javascript
// ✅ 正确
$('#kiContent').summernote('code', item.content);
// ❌ 错误
document.getElementById('kiContent').value = item.content;
```

**陷阱2 — 读取内容**：同样用 `.summernote('code')`：
```javascript
// ✅ 正确
var content = $('#kiContent').summernote('code');
// ❌ 错误
var content = document.getElementById('kiContent').value;
```

**陷阱3 — 编辑回填**：先 fetch 数据，再填表单：
```javascript
function editItem(id) {
    fetch('/admin/api/knowledge/' + id)
        .then(r => r.json())
        .then(res => {
            var item = res.item;
            document.getElementById('editForm').elements['id'].value = item.id;
            document.getElementById('editForm').elements['title'].value = item.title;
            document.getElementById('editForm').elements['category_id'].value = item.category_id;
            $('#kiContent').summernote('code', item.content || '');
            // ... 其他字段
            new bootstrap.Modal('#editModal').show();
        });
}
```

### 5.4 批量删除的最佳实践

```javascript
function batchDelete(ids) {
    if (!confirm('确定要删除选中的 ' + ids.length + ' 条记录吗？此操作不可恢复！')) return;
    
    var promises = ids.map(function(id) {
        return fetch('/admin/api/knowledge/' + id, { method: 'DELETE' })
            .then(r => r.json());
    });
    
    Promise.allSettled(promises)
        .then(function(results) {
            var succeeded = results.filter(r => r.value && r.value.success).length;
            alert('成功删除 ' + succeeded + ' 条');
            location.reload();
        });
}
```

---

## 六、定时调度

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    crawl_job,              # 需要在 app.app_context() 中执行
    'interval',
    minutes=60,             # config.CRAWL_INTERVAL_MINUTES
    id='policy_crawl',
    name='定时抓取',
    replace_existing=True,
)
scheduler.start()
```

**关键**：job 函数必须包裹 `with app.app_context():`。

---

## 七、常见问题与修复

| 问题 | 原因 | 修复 |
|------|------|------|
| 抓取不到内容 | CSS选择器与页面结构不匹配 | 改用智能提取（分析ul/ol，找含链接最多的列表） |
| HTTP 412/403 | 目标站有 WAF 或反爬 | 换用替代URL、添加完整请求头 |
| 编辑弹窗内容为空 | 缺少GET端点 + 前端未回填 | 新增 `/api/xxx/<id>` GET端点 + fetch数据回填 |
| Summernote内容不保存 | 用 `.value` 而非 `.summernote('code')` | 始终用 Summernote 专有 API |
| 批量操作按钮失效 | 事件委托不可靠 | 改用 `onchange="updateBtns()"` 内联属性 |
| 父分类计数不完整 | 未统计子分类条目 | `_get_category_ids()` 收集子分类ID再查询 |
| Flask启动路径错误 | Windows路径分隔符 | 用 `python.exe "G:/web/project/app.py"` 完整路径 |
| Scrapling auto_rotate 警告 | 参数已废弃 | 去掉 `auto_rotate` 参数 |

---

## 八、适配新领域的步骤

按照以下步骤将平台适配到新的内容领域：

### Step 1: 重新设计数据模型

修改 `models.py` 中的字段名和分类体系：
- `Policy` → 可改名为 `Article` / `Patent` / `Report` 等
- `Category` 初始化改领域相关的分类树
- `MonitorSource` 的 category 枚举值

### Step 2: 配置数据源

修改 `crawler.py` 中 `seed_default_sources()` 的预置URL列表。每个数据源需提供：
- 目标网站URL（**先手动检查是否有WAF保护**）
- 分类标签
- 可选CSS选择器配置

### Step 3: 定制智能分类

修改 `admin.py` 中 `CATEGORY_KEYWORDS` 字典，建立领域关键词→分类的映射。权重设计原则：
- 精准关键词（如"医疗纠纷"→医疗法规）权重设为15-20
- 宽泛关键词（如"管理"→管理指南）权重设为5-8
- 同一个关键词可映射到多个相关分类

### Step 4: 调整前端模板

- `base.html` 的导航菜单项
- 首页统计卡片的指标名称
- 列表页的表格列头
- 品牌配色（CSS变量 `--navy` / `--gold`）

### Step 5: 预置种子数据

在 `app.py` 的 `_ensure_admin_user()` 附近添加初始分类、初始知识条目的创建逻辑。

---

## 九、部署检查清单

- [ ] SQLite 数据库文件路径正确（`instance/` 目录）
- [ ] `instance/` 目录已加入 `.gitignore`
- [ ] 管理后台受 session 认证保护
- [ ] 爬虫降级机制可用（Scrapling → requests）
- [ ] 至少一个数据源手动测试抓取成功
- [ ] 批量操作（选择/修改/删除/转入）全部测试通过
- [ ] 知识库编辑（Summernote 加载 + 保存）正常
- [ ] 分类计数准确（父分类 = 自身 + 所有子分类之和）
- [ ] 定时调度器间隔合理
- [ ] 配色在移动端显示正常
