"""
档案政策监控与知识库平台 - 配置文件
Hospital Archive Policy Monitor & Knowledge Base - Configuration
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'archive-kb-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "instance", "archive.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CRAWL_INTERVAL_MINUTES = int(os.environ.get('CRAWL_INTERVAL', 60))
    CRAWL_RETRY_COUNT = 3
    CRAWL_TIMEOUT_SECONDS = 30
    USER_AGENT = 'ArchiveKB/1.0 (Hospital Policy Monitor)'

    ITEMS_PER_PAGE = 20
    ENABLE_SCHEDULER = os.environ.get('ENABLE_SCHEDULER', 'true').lower() == 'true'
