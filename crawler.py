"""
Scrapling 爬虫模块 - 政策法规采集引擎
"""
import json
import hashlib
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_hash(text: str) -> str:
    """计算内容哈希用于去重"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class PolicyCrawler:
    """政策监控爬虫 - 使用 Scrapling"""

    def __init__(self, db_session):
        self.db = db_session

    def crawl_source(self, source):
        """爬取单个数据源"""
        from models import MonitorSource, MonitorLog, Policy

        start_time = time.time()
        log_entry = MonitorLog(source_id=source.id, status='running')
        self.db.add(log_entry)
        self.db.flush()

        try:
            items = self._fetch_items(source)
            log_entry.items_found = len(items)
            new_count = 0

            from sqlalchemy import func
            for item in items:
                content_text = f"{item.get('title', '')}{item.get('content', '')}"
                content_hash = compute_hash(content_text)

                existing = Policy.query.filter_by(content_hash=content_hash).first()
                if existing:
                    continue

                policy = Policy(
                    source_id=source.id,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    summary=item.get('summary', ''),
                    content=item.get('content', ''),
                    pub_date=item.get('pub_date'),
                    authority=item.get('authority', ''),
                    doc_number=item.get('doc_number', ''),
                    file_type=item.get('file_type', '通知'),
                    tags=item.get('tags', ''),
                    content_hash=content_hash,
                )
                self.db.add(policy)
                new_count += 1

            log_entry.items_new = new_count
            log_entry.status = 'success'
            source.last_crawl_status = 'success'

            self.db.commit()
            logger.info(f"[{source.name}] 抓取完成: 发现{len(items)}条, 新增{new_count}条")

        except Exception as e:
            log_entry.status = 'error'
            log_entry.error_message = str(e)
            source.last_crawl_status = 'error'
            self.db.commit()
            logger.error(f"[{source.name}] 抓取失败: {e}")

        finally:
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            source.last_crawl_at = datetime.utcnow()
            self.db.commit()

    def _fetch_items(self, source):
        """根据数据源类型执行抓取"""
        if source.crawl_method == 'stealthy':
            return self._stealthy_fetch(source)
        elif source.crawl_method == 'fetch':
            return self._dynamic_fetch(source)
        else:
            return self._simple_get(source)

    def _simple_get(self, source):
        """HTTP GET 方式抓取"""
        try:
            from scrapling import Fetcher
            fetcher = Fetcher(auto_rotate=False)
            page = fetcher.get(source.url, impersonate='chrome')

            return self._extract_items(page, source)
        except ImportError:
            return self._fallback_requests(source)

    def _dynamic_fetch(self, source):
        """动态浏览器抓取"""
        try:
            from scrapling import PlayWrightFetcher
            fetcher = PlayWrightFetcher()
            page = fetcher.fetch(source.url, headless=True)

            return self._extract_items(page, source)
        except ImportError:
            return self._fallback_requests(source)

    def _stealthy_fetch(self, source):
        """隐身模式抓取(绕过Cloudflare等)"""
        try:
            from scrapling import StealthyFetcher
            fetcher = StealthyFetcher(auto_rotate=True)
            page = fetcher.stealthy_fetch(source.url)

            return self._extract_items(page, source)
        except ImportError:
            return self._simple_get(source)

    def _extract_items(self, page, source):
        """从页面提取条目数据"""
        items = []
        selectors = {}

        if source.selectors:
            try:
                selectors = json.loads(source.selectors)
            except json.JSONDecodeError:
                selectors = {}

        container_sel = selectors.get('container', 'article, .item, .list-item, li')
        title_sel = selectors.get('title', 'a, h2, h3, .title')
        date_sel = selectors.get('date', '.date, .time, time, span')
        link_sel = selectors.get('link', 'a')

        containers = page.css(container_sel)

        for el in containers:
            title_el = el.css(title_sel).first
            if not title_el:
                continue

            title = title_el.text.strip()
            if not title or len(title) < 3:
                continue

            item_url = ''
            link_el = el.css(link_sel).first
            if link_el:
                href = link_el.attr('href')
                if href:
                    item_url = href if href.startswith('http') else page.url.rstrip('/') + '/' + href.lstrip('/')

            date_str = ''
            date_el = el.css(date_sel).first
            if date_el:
                date_str = date_el.text.strip()

            pub_date = None
            if date_str:
                pub_date = self._parse_date(date_str)

            body_text = ''
            body_el = el.css('p, .summary, .desc').first
            if body_el:
                body_text = body_el.text.strip()[:500]

            items.append({
                'title': title,
                'url': item_url,
                'summary': body_text,
                'content': el.get()[:2000] if hasattr(el, 'get') else '',
                'pub_date': pub_date,
                'authority': '',
                'doc_number': '',
                'file_type': '通知',
                'tags': source.category,
            })

        return items

    def _fallback_requests(self, source):
        """使用 requests 作为降级方案"""
        import requests
        from bs4 import BeautifulSoup

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(source.url, headers=headers, timeout=30)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = []

            containers = soup.select('article, .item, .list-item, li')
            if not containers:
                containers = soup.find_all(['div', 'li'])

            for el in containers:
                title_el = el.find(['a', 'h2', 'h3'])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                link = ''
                if title_el.name == 'a':
                    link = title_el.get('href', '')
                else:
                    a_tag = el.find('a')
                    if a_tag:
                        link = a_tag.get('href', '')
                if link and not link.startswith('http'):
                    link = resp.url.rstrip('/') + '/' + link.lstrip('/')

                date_tag = el.find(['span', 'time'], class_=lambda c: c and any(k in (c or '') for k in ['date', 'time']))
                date_str = date_tag.get_text(strip=True) if date_tag else ''

                items.append({
                    'title': title,
                    'url': link,
                    'summary': '',
                    'content': '',
                    'pub_date': self._parse_date(date_str),
                    'authority': '',
                    'doc_number': '',
                    'file_type': '通知',
                    'tags': source.category,
                })
            return items

        except Exception as e:
            logger.error(f"fallback抓取失败: {e}")
            return []

    @staticmethod
    def _parse_date(date_str: str):
        """解析日期字符串"""
        if not date_str:
            return None
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日', '%m月%d日']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def crawl_all_enabled(self):
        """爬取所有启用的数据源"""
        from models import MonitorSource
        sources = MonitorSource.query.filter_by(enabled=True).all()
        for source in sources:
            try:
                self.crawl_source(source)
            except Exception as e:
                logger.error(f"数据源 [{source.name}] 整体失败: {e}")

    def seed_default_sources(self):
        """初始化预置数据源"""
        from models import MonitorSource

        defaults = [
            {
                'name': '国家档案局 - 政策法规',
                'url': 'https://www.saac.gov.cn/',
                'source_type': 'web',
                'category': '档案局',
                'crawl_method': 'get',
                'selectors': json.dumps({
                    'container': '.news_list li, .list-item',
                    'title': 'a',
                    'date': 'span',
                    'link': 'a',
                }, ensure_ascii=False),
            },
            {
                'name': '国家卫健委 - 政策文件',
                'url': 'http://www.nhc.gov.cn/wjw/zcjd/list.shtml',
                'source_type': 'web',
                'category': '卫健委',
                'crawl_method': 'get',
                'selectors': json.dumps({
                    'container': '.list-item, li',
                    'title': 'a',
                    'date': 'span',
                    'link': 'a',
                }, ensure_ascii=False),
            },
            {
                'name': '国家法律法规数据库',
                'url': 'https://flk.npc.gov.cn/',
                'source_type': 'web',
                'category': '法律法规',
                'crawl_method': 'get',
                'selectors': json.dumps({
                    'container': '.list-item, li',
                    'title': 'a, span',
                    'date': 'span',
                    'link': 'a',
                }, ensure_ascii=False),
            },
            {
                'name': '中国政府网 - 政策',
                'url': 'https://www.gov.cn/zhengce/',
                'source_type': 'web',
                'category': '法律法规',
                'crawl_method': 'get',
                'selectors': json.dumps({
                    'container': '.news_box li, .listTxt li',
                    'title': 'a',
                    'date': '.date',
                    'link': 'a',
                }, ensure_ascii=False),
            },
            {
                'name': '中国医院协会 - 行业动态',
                'url': 'https://www.cha.org.cn/',
                'source_type': 'web',
                'category': '行业动态',
                'crawl_method': 'get',
                'selectors': json.dumps({
                    'container': '.news-list li, .list-item',
                    'title': 'a',
                    'date': 'span',
                    'link': 'a',
                }, ensure_ascii=False),
            },
        ]

        for d in defaults:
            existing = MonitorSource.query.filter_by(url=d['url']).first()
            if not existing:
                source = MonitorSource(**d)
                self.db.add(source)
        self.db.commit()
        logger.info(f'已初始化 {len(defaults)} 个预置数据源')
