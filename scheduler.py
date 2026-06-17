"""
定时调度模块 - APScheduler 集成
"""
import logging

logger = logging.getLogger(__name__)

scheduler = None


def init_scheduler(app):
    """初始化定时调度器"""
    if not app.config.get('ENABLE_SCHEDULER', True):
        logger.info('调度器已禁用')
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        global scheduler
        scheduler = BackgroundScheduler(daemon=True)

        interval = app.config.get('CRAWL_INTERVAL_MINUTES', 60)

        def crawl_job():
            with app.app_context():
                from models import db
                from crawler import PolicyCrawler, NewsCrawler
                
                # 抓取政策法规
                try:
                    policy_crawler = PolicyCrawler(db.session)
                    policy_crawler.crawl_all_enabled()
                    logger.info('定时任务：政策法规抓取完成')
                except Exception as e:
                    logger.error(f'定时任务：政策法规抓取失败 - {e}')
                
                # 抓取行业资讯
                try:
                    news_crawler = NewsCrawler(db.session)
                    news_crawler.crawl_all_enabled()
                    logger.info('定时任务：行业资讯抓取完成')
                except Exception as e:
                    logger.error(f'定时任务：行业资讯抓取失败 - {e}')

        scheduler.add_job(
            crawl_job,
            'interval',
            minutes=interval,
            id='policy_crawl',
            name='政策定时抓取',
            replace_existing=True,
        )

        scheduler.start()
        logger.info(f'调度器已启动，抓取间隔 {interval} 分钟')

    except ImportError:
        logger.warning('APScheduler 未安装，调度器不可用')
        return None

    return scheduler


def trigger_crawl(app):
    """手动触发一次全量抓取"""
    with app.app_context():
        from models import db
        from crawler import PolicyCrawler
        crawler = PolicyCrawler(db.session)
        crawler.crawl_all_enabled()
