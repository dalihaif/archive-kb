"""
档案政策监控与知识库平台
Hospital Archive Policy Monitor & Knowledge Base
"""
import hashlib
import logging
from flask import Flask
from config import Config
from models import db, User, init_fts, init_news_sources

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from routes.main import main_bp
    from routes.admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _migrate_db()
        init_fts()
        _ensure_admin_user()

    from scheduler import init_scheduler
    init_scheduler(app)

    return app


def _migrate_db():
    """处理数据库迁移（新增列）"""
    import sqlite3, os
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'archive.db')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columns = [r[1] for r in cur.fetchall()]
    if 'alert_keywords' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN alert_keywords VARCHAR(1000) DEFAULT ''")
        conn.commit()
        logger.info('数据库迁移: 已添加 users.alert_keywords 列')
    conn.close()


def _ensure_admin_user():
    """确保至少有一个管理员用户"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=hashlib.sha256('admin123'.encode()).hexdigest(),
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        logger.info('已创建默认管理员账户: admin / admin123')

    # 初始化预置数据源
    from crawler import PolicyCrawler
    crawler = PolicyCrawler(db.session)
    crawler.seed_default_sources()

    # 初始化知识库默认分类
    from models import Category
    if Category.query.count() == 0:
        defaults = [
            ('档案法规', 0, 'bi-journal-text', '档案管理相关法律法规'),
            ('行业标准', 0, 'bi-clipboard-check', 'DA/T、ISO等档案行业标准'),
            ('政策文件', 0, 'bi-file-earmark-text', '卫健委、档案局等政策文件'),
            ('工作指南', 0, 'bi-book', '档案工作实操指南与方法论'),
            ('档案法规 > 国家法律', None, 'bi-journal-bookmark', ''),
            ('档案法规 > 行政法规', None, 'bi-journal', ''),
            ('档案法规 > 地方法规', None, 'bi-journal-album', ''),
            ('行业标准 > DA/T标准', None, 'bi-clipboard', ''),
            ('行业标准 > 国际标准', None, 'bi-globe2', ''),
            ('政策文件 > 卫健委', None, 'bi-hospital', ''),
            ('政策文件 > 档案局', None, 'bi-archive', ''),
            ('工作指南 > 分类编目', None, 'bi-tags', ''),
            ('工作指南 > 数字化', None, 'bi-cpu', ''),
            ('工作指南 > 保管保护', None, 'bi-shield-check', ''),
        ]
        parent_map = {}
        for name, parent_id, icon, desc in defaults:
            if parent_id == 0:
                cat = Category(name=name, parent_id=None, sort_order=0, icon=icon, description=desc)
                db.session.add(cat)
                db.session.flush()
                parent_map[name] = cat.id

        for name, parent_id, icon, desc in defaults:
            if parent_id is None:
                parent_key = name.split(' > ')[0]
                cat = Category(
                    name=name.split(' > ')[1],
                    parent_id=parent_map.get(parent_key),
                    sort_order=0, icon=icon, description=desc
                )
                db.session.add(cat)

        db.session.commit()
        logger.info('已初始化知识库默认分类')

        # 初始化国内外档案行业数据源
        init_news_sources()
        logger.info('已初始化国内外档案行业数据源')


if __name__ == '__main__':
    app = create_app()
    logger.info('档案政策监控与知识库平台启动')
    app.run(host='0.0.0.0', port=5050, debug=True)
