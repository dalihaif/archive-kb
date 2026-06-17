# 档案政策监控与知识库平台

基于 Flask + SQLite + Scrapling + Bootstrap5 构建的医院档案管理知识平台。

## 功能
- 政策法规自动监控（国家档案局、卫健委、法律法规数据库）
- 知识库分类管理与检索
- 定时自动抓取（60分钟间隔）
- 管理后台（数据源管理、政策管理、知识库管理）

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

访问 http://127.0.0.1:5050
后台 http://127.0.0.1:5050/admin (admin/admin123)
