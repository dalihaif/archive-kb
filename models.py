"""
数据库模型 - 政策监控与知识库
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class MonitorSource(db.Model):
    """监控数据源"""
    __tablename__ = 'monitor_sources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False, comment='数据源名称')
    url = db.Column(db.String(500), nullable=False, comment='目标URL')
    source_type = db.Column(db.String(50), nullable=False, default='web', comment='类型: web/rss/api')
    category = db.Column(db.String(100), nullable=False, comment='分类: 卫健委/档案局/法律法规/行业标准/学术文献/同行实践')
    crawl_method = db.Column(db.String(20), default='get', comment='爬取方式: get/fetch/stealthy')
    selectors = db.Column(db.Text, comment='CSS选择器配置(JSON)')
    enabled = db.Column(db.Boolean, default=True, comment='是否启用')
    last_crawl_at = db.Column(db.DateTime, comment='最后爬取时间')
    last_crawl_status = db.Column(db.String(20), comment='最后爬取状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs = db.relationship('MonitorLog', backref='source', lazy='dynamic', cascade='all, delete-orphan')
    policies = db.relationship('Policy', backref='source', lazy='dynamic', cascade='all, delete-orphan')


class MonitorLog(db.Model):
    """监控日志"""
    __tablename__ = 'monitor_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey('monitor_sources.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, comment='success/error/timeout')
    items_found = db.Column(db.Integer, default=0, comment='抓取到的条目数')
    items_new = db.Column(db.Integer, default=0, comment='新增条目数')
    error_message = db.Column(db.Text, comment='错误信息')
    duration_ms = db.Column(db.Integer, comment='耗时(毫秒)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Policy(db.Model):
    """政策法规条目"""
    __tablename__ = 'policies'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey('monitor_sources.id'))
    title = db.Column(db.String(500), nullable=False, comment='标题')
    url = db.Column(db.String(1000), comment='原始链接')
    summary = db.Column(db.Text, comment='摘要')
    content = db.Column(db.Text, comment='正文内容(HTML)')
    pub_date = db.Column(db.Date, comment='发布日期')
    authority = db.Column(db.String(200), comment='发布机构')
    doc_number = db.Column(db.String(200), comment='文号')
    file_type = db.Column(db.String(50), comment='文件类型: 通知/公告/法规/标准/案例')
    tags = db.Column(db.String(500), comment='标签(逗号分隔)')
    is_pinned = db.Column(db.Boolean, default=False, comment='是否置顶')
    is_read = db.Column(db.Boolean, default=False, comment='是否已读')
    view_count = db.Column(db.Integer, default=0)
    content_hash = db.Column(db.String(64), comment='内容哈希(去重)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_policy_hash', 'content_hash'),
        db.Index('idx_policy_pub_date', 'pub_date'),
        db.Index('idx_policy_source', 'source_id'),
    )


class Category(db.Model):
    """知识库分类"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False, comment='分类名称')
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), comment='上级分类')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    icon = db.Column(db.String(50), comment='图标类名')
    description = db.Column(db.String(500), comment='描述')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Category', remote_side=[id], backref='children')
    knowledge_items = db.relationship('KnowledgeItem', backref='category', lazy='dynamic')


class KnowledgeItem(db.Model):
    """知识库条目"""
    __tablename__ = 'knowledge_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False, comment='标题')
    content = db.Column(db.Text, comment='内容(HTML)')
    source = db.Column(db.String(500), comment='来源')
    source_url = db.Column(db.String(1000), comment='来源链接')
    tags = db.Column(db.String(500), comment='标签')
    is_pinned = db.Column(db.Boolean, default=False, comment='置顶')
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_ki_category', 'category_id'),
        db.Index('idx_ki_created', 'created_at'),
    )


class User(db.Model):
    """管理员用户"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    alert_keywords = db.Column(db.String(1000), default='', comment='关注关键词(逗号分隔)')
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class News(db.Model):
    """行业资讯条目"""
    __tablename__ = 'news'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey('monitor_sources.id'), comment='数据源ID')
    title = db.Column(db.String(500), nullable=False, comment='标题')
    url = db.Column(db.String(1000), comment='原始链接')
    summary = db.Column(db.Text, comment='摘要')
    content = db.Column(db.Text, comment='正文内容')
    pub_date = db.Column(db.DateTime, comment='发布时间')
    source_name = db.Column(db.String(200), comment='来源名称(冗余)')
    country = db.Column(db.String(50), default='中国', comment='国家/地区')
    language = db.Column(db.String(20), default='zh', comment='语言: zh/en')
    tags = db.Column(db.String(500), comment='标签(逗号分隔)')
    is_read = db.Column(db.Boolean, default=False, comment='是否已读')
    view_count = db.Column(db.Integer, default=0)
    content_hash = db.Column(db.String(64), comment='内容哈希(去重)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_news_hash', 'content_hash'),
        db.Index('idx_news_pub_date', 'pub_date'),
        db.Index('idx_news_source', 'source_id'),
        db.Index('idx_news_country', 'country'),
    )


def init_fts():
    """初始化全文搜索索引"""
    from sqlalchemy import text
    db.session.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS policies_fts
        USING fts5(title, content, summary, tags, content=policies, content_rowid=id);
    """))
    # 重建触发器：保持 FTS 索引与 policies 表同步
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS policies_ai AFTER INSERT ON policies BEGIN
            INSERT INTO policies_fts(rowid, title, content, summary, tags)
            VALUES (new.id, new.title, new.content, new.summary, new.tags);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS policies_ad AFTER DELETE ON policies BEGIN
            INSERT INTO policies_fts(policies_fts, rowid, title, content, summary, tags)
            VALUES ('delete', old.id, old.title, old.content, old.summary, old.tags);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS policies_au AFTER UPDATE ON policies BEGIN
            INSERT INTO policies_fts(policies_fts, rowid, title, content, summary, tags)
            VALUES ('delete', old.id, old.title, old.content, old.summary, old.tags);
            INSERT INTO policies_fts(rowid, title, content, summary, tags)
            VALUES (new.id, new.title, new.content, new.summary, new.tags);
        END;
    """))
    db.session.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
        USING fts5(title, content, tags, content=knowledge_items, content_rowid=id);
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_items BEGIN
            INSERT INTO knowledge_fts(rowid, title, content, tags)
            VALUES (new.id, new.title, new.content, new.tags);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_items BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags)
            VALUES ('delete', old.id, old.title, old.content, old.tags);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_items BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags)
            VALUES ('delete', old.id, old.title, old.content, old.tags);
            INSERT INTO knowledge_fts(rowid, title, content, tags)
            VALUES (new.id, new.title, new.content, new.tags);
        END;
    """))
    # 填充已有数据
    db.session.execute(text("""
        INSERT OR IGNORE INTO policies_fts(rowid, title, content, summary, tags)
        SELECT id, title, content, summary, tags FROM policies;
    """))
    db.session.execute(text("""
        INSERT OR IGNORE INTO knowledge_fts(rowid, title, content, tags)
        SELECT id, title, content, tags FROM knowledge_items;
    """))
    # News 表全文搜索索引
    db.session.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS news_fts
        USING fts5(title, content, summary, tags, source_name, content=news, content_rowid=id);
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS news_ai AFTER INSERT ON news BEGIN
            INSERT INTO news_fts(rowid, title, content, summary, tags, source_name)
            VALUES (new.id, new.title, new.content, new.summary, new.tags, new.source_name);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS news_ad AFTER DELETE ON news BEGIN
            INSERT INTO news_fts(news_fts, rowid, title, content, summary, tags, source_name)
            VALUES ('delete', old.id, old.title, old.content, old.summary, old.tags, old.source_name);
        END;
    """))
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS news_au AFTER UPDATE ON news BEGIN
            INSERT INTO news_fts(news_fts, rowid, title, content, summary, tags, source_name)
            VALUES ('delete', old.id, old.title, old.content, old.summary, old.tags, old.source_name);
            INSERT INTO news_fts(rowid, title, content, summary, tags, source_name)
            VALUES (new.id, new.title, new.content, new.summary, new.tags, new.source_name);
        END;
    """))
    db.session.execute(text("""
        INSERT OR IGNORE INTO news_fts(rowid, title, content, summary, tags, source_name)
        SELECT id, title, content, summary, tags, source_name FROM news;
    """))
    db.session.commit()


def init_news_sources():
    """初始化国内外档案行业数据源"""
    sources = [
        # 国内数据源
        {
            'name': '国家档案局',
            'url': 'https://www.saac.gov.cn/',
            'source_type': 'web',
            'category': '国内-政府机构',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-list li", "title": ".title", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '中国档案学会',
            'url': 'http://www.china-archives.cn/',
            'source_type': 'web',
            'category': '国内-学术组织',
            'crawl_method': 'get',
            'selectors': '{"list": ".list-item", "title": "a", "link": "a::attr(href)", "date": ".time"}',
            'enabled': True
        },
        {
            'name': '档案界',
            'url': 'http://www.danganj.com/',
            'source_type': 'web',
            'category': '国内-行业网站',
            'crawl_method': 'get',
            'selectors': '{"list": ".post", "title": "h2 a", "link": "h2 a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '各省档案局微博聚合',
            'url': 'https://weibo.com/',
            'source_type': 'api',
            'category': '国内-社交媒体',
            'crawl_method': 'get',
            'selectors': '',
            'enabled': False  # 需要API密钥
        },
        # 国际数据源
        {
            'name': '国际档案理事会(ICA)',
            'url': 'https://www.ica.org/en/news',
            'source_type': 'web',
            'category': '国际-国际组织',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3 a", "link": "h3 a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '美国国家档案馆',
            'url': 'https://www.archives.gov/news',
            'source_type': 'web',
            'category': '国际-国家档案馆',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-teaser", "title": "h3 a", "link": "h3 a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '英国国家档案馆',
            'url': 'https://www.nationalarchives.gov.uk/about/news/',
            'source_type': 'web',
            'category': '国际-国家档案馆',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '澳大利亚国家档案馆',
            'url': 'https://www.naa.gov.au/news',
            'source_type': 'web',
            'category': '国际-国家档案馆',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': '加拿大图书档案馆',
            'url': 'https://www.bac-lac.gc.ca/eng/news/Pages/default.aspx',
            'source_type': 'web',
            'category': '国际-国家档案馆',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': 'Archives & Records Association (UK)',
            'url': 'https://www.archives.org.uk/news',
            'source_type': 'web',
            'category': '国际-专业协会',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
        {
            'name': 'Society of American Archivists',
            'url': 'https://www2.archivists.org/news',
            'source_type': 'web',
            'category': '国际-专业协会',
            'crawl_method': 'get',
            'selectors': '{"list": ".news-item", "title": "h3", "link": "a::attr(href)", "date": ".date"}',
            'enabled': True
        },
    ]

    for src in sources:
        existing = MonitorSource.query.filter_by(name=src['name']).first()
        if not existing:
            source = MonitorSource(**src)
            db.session.add(source)

    db.session.commit()
