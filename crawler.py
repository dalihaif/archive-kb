"""
Scrapling 爬虫模块 - 政策法规采集引擎
支持三级抓取策略 + 智能内容提取
"""
import json
import re
import hashlib
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_hash(text: str) -> str:
    """计算内容哈希用于去重"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class PolicyCrawler:
    """政策监控爬虫 - Scrapling + 智能提取"""

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
        """根据数据源类型获取HTML，然后智能提取内容"""
        # 第一步：获取页面HTML
        html, base_url = self._download_page(source)

        if html is None:
            logger.error(f"[{source.name}] 无法获取页面内容")
            return []

        # 第二步：智能提取内容条目
        items = self._smart_extract(html, base_url, source)

        # 第三步：抓取详情页正文（最多抓前5条，避免过慢）
        if items:
            fetch_limit = min(5, len(items))
            logger.info(f"[{source.name}] 开始抓取 {fetch_limit} 条详情页全文...")
            for i, item in enumerate(items[:fetch_limit]):
                if item.get('url'):
                    try:
                        detail_html, _ = self._download_detail_page(item['url'])
                        if detail_html:
                            content = self._extract_article_content(detail_html)
                            if content:
                                item['content'] = content
                                item['summary'] = content[:300] if not item.get('summary') else item['summary']
                                logger.info(f"[{source.name}] 详情页全文抓取成功: {item['title'][:40]}...")
                    except Exception as e:
                        logger.warning(f"[{source.name}] 详情页抓取失败: {item['title'][:40]}... {e}")
                time.sleep(0.5)  # 礼貌延迟

        return items

    def _download_page(self, source):
        """下载页面HTML，返回 (html_str, base_url)"""
        # 优先使用 Scrapling（更好的 TLS 指纹伪装）
        try:
            from scrapling import Fetcher
            fetcher = Fetcher()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Cache-Control': 'no-cache',
            }
            page = fetcher.get(source.url, impersonate='chrome', timeout=30, headers=headers)

            status_code = getattr(page, 'status', 0) or 0
            if page.body and status_code < 400:
                html = page.body.decode('utf-8', errors='replace') if isinstance(page.body, bytes) else page.body
                logger.info(f"[{source.name}] Scrapling 获取成功, 大小 {len(html)} 字节")
                return html, page.url
            elif status_code >= 400:
                raise Exception(f"HTTP {status_code}")

        except ImportError:
            logger.warning("Scrapling 未安装, 使用 requests")
        except Exception as e:
            logger.warning(f"Scrapling 获取失败: {e}, 降级到 requests")

        # 降级方案：requests
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        try:
            resp = requests.get(source.url, headers=headers, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            logger.info(f"[{source.name}] requests 获取成功, 大小 {len(resp.text)} 字节")
            return resp.text, resp.url
        except Exception as e:
            logger.error(f"[{source.name}] requests 获取失败: {e}")
            return None, source.url

    def _download_detail_page(self, url):
        """下载详情页HTML，返回 (html_str, base_url)"""
        try:
            from scrapling import Fetcher
            fetcher = Fetcher()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.5',
            }
            page = fetcher.get(url, impersonate='chrome', timeout=20, headers=headers)
            if page.body:
                html = page.body.decode('utf-8', errors='replace') if isinstance(page.body, bytes) else page.body
                return html, page.url
        except Exception:
            pass

        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return resp.text, resp.url
        except Exception:
            return None, url

    @staticmethod
    def _extract_article_content(html):
        """从文章详情页提取正文内容"""
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, 'html.parser')

        # 移除噪音
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'noscript', 'iframe', 'header']):
            tag.decompose()

        # 策略：找最可能的内容容器
        candidates = []
        content_selectors = [
            'article', '.article', '.content', '.main-content', '#content',
            '.article-content', '.post-content', '.entry-content',
            '.TRS_Editor', '.Custom_UnionStyle', '.pages_content',
            '.con', '.detail', '.info', '#zoom', '.text',
            '.news-content', '.xw-content', '[class*="article"]', '[class*="content"]',
        ]

        for sel in content_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if len(text) >= 200:
                    candidates.append((len(text), el))

        if not candidates:
            # 兜底：取 <body> 中纯文本最长的区域
            for el in soup.find_all(['div', 'section', 'main']):
                text = el.get_text(strip=True)
                if 200 <= len(text) <= 50000:
                    candidates.append((len(text), el))

        if candidates:
            candidates.sort(key=lambda x: -x[0])
            el = candidates[0][1]
            # 返回清理后的HTML
            for tag in el.find_all(True):
                if tag.name in ['a']:
                    tag.unwrap()  # 去掉链接但保留文本
            return el.prettify()

        return None

    def _smart_extract(self, html, base_url, source):
        """智能提取：自动识别页面内容列表，无需预先配置CSS选择器"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # 移除噪音元素
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'noscript', 'iframe']):
            tag.decompose()

        # 策略1：使用用户配置的选择器
        if source.selectors:
            items = self._extract_via_selectors(soup, source, base_url)
            if items:
                logger.info(f"[{source.name}] 选择器提取: {len(items)}条")
                return items

        # 策略2：智能发现内容列表
        items = self._extract_via_list_heuristic(soup, base_url)
        if items:
            logger.info(f"[{source.name}] 列表启发式提取: {len(items)}条")
            return items

        # 策略3：提取所有实质性链接
        items = self._extract_via_links(soup, base_url)
        logger.info(f"[{source.name}] 链接提取: {len(items)}条")
        return items

    def _extract_via_selectors(self, soup, source, base_url):
        """通过用户配置的CSS选择器提取"""
        try:
            selectors = json.loads(source.selectors)
        except (json.JSONDecodeError, TypeError):
            return []

        container_sel = selectors.get('container', '')
        if not container_sel:
            return []

        containers = soup.select(container_sel)
        if not containers:
            return []

        items = []
        title_sel = selectors.get('title', 'a, h2, h3, .title')
        date_sel = selectors.get('date', '.date, .time, time, span')
        link_sel = selectors.get('link', 'a')

        for el in containers:
            # 提取标题
            title_el = el.select_one(title_sel) if title_sel else el.find(['a', 'h2', 'h3'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # 提取链接
            link = ''
            link_el = el.select_one(link_sel) if link_sel else el.find('a')
            if link_el and link_el.get('href'):
                link = link_el['href']
                if not link.startswith('http'):
                    link = base_url.rstrip('/') + '/' + link.lstrip('/')

            # 提取日期
            date_str = ''
            date_el = el.select_one(date_sel) if date_sel else None
            if date_el:
                date_str = date_el.get_text(strip=True)

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

    def _extract_via_list_heuristic(self, soup, base_url):
        """启发式提取：找到页面中内容最丰富的 <ul>/<ol> 列表"""
        all_lists = soup.find_all(['ul', 'ol'])
        candidates = []

        for lst in all_lists:
            lis = lst.find_all('li')
            content_items = []
            for li in lis:
                a = li.find('a', href=True)
                if a:
                    text = a.get_text(strip=True)
                    if len(text) >= 10:
                        content_items.append((li, a, text))

            if len(content_items) >= 3:
                # 过滤明显是导航菜单的（链接文本都很短）
                avg_len = sum(len(item[2]) for item in content_items) / len(content_items)
                if avg_len >= 12:
                    candidates.append((content_items, len(content_items)))

        if not candidates:
            return []

        # 合并所有合格列表的内容（去重）
        seen_titles = set()
        items = []

        for content_items, _ in candidates:
            for li, a, title in content_items:
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                href = a.get('href', '')
                if href and not href.startswith('http'):
                    href = base_url.rstrip('/') + '/' + href.lstrip('/')

                # 智能日期提取
                date_str = self._find_date_in_element(li)

                items.append({
                    'title': title,
                    'url': href,
                    'summary': '',
                    'content': '',
                    'pub_date': self._parse_date(date_str),
                    'authority': '',
                    'doc_number': '',
                    'file_type': '通知',
                    'tags': '',
                })

        return items

    def _extract_via_links(self, soup, base_url):
        """兜底方案：提取所有有意义的链接"""
        # 常见的导航链接文本
        nav_patterns = [
            '首页', '登录', '注册', '更多', '设为首页', '加入收藏',
            '网站地图', '联系我们', '关于我们', '返回', '关闭',
            '下一页', '上一页', '首页', '尾页', 'English', 'EN',
            'Home', '首页', '机构概况', '新闻动态', '政务公开',
            '首页', '搜索', '高级搜索', '简体', '繁体',
        ]

        items = []
        seen_titles = set()
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            if text in nav_patterns:
                continue
            if text in seen_titles:
                continue
            seen_titles.add(text)

            # 排除纯数字/日期格式的文本
            if re.match(r'^[\d\-–—/\.\s]+$', text):
                continue

            href = a['href']
            if not href.startswith('http'):
                href = base_url.rstrip('/') + '/' + href.lstrip('/')

            items.append({
                'title': text,
                'url': href,
                'summary': '',
                'content': '',
                'pub_date': None,
                'authority': '',
                'doc_number': '',
                'file_type': '通知',
                'tags': '',
            })

        return items

    def _find_date_in_element(self, el):
        """在元素中智能查找日期"""
        # 方案1：查找 <span> 中可能包含日期的文本
        for tag in el.find_all('span'):
            text = tag.get_text(strip=True)
            if self._looks_like_date(text):
                return text

        # 方案2：使用正则在整个元素文本中匹配日期
        text = el.get_text()
        date_patterns = [
            r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',      # 2026-01-15, 2026年1月15日
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',                 # 2026/01/15
            r'\[(\d{4}-\d{2}-\d{2})\]',                         # [2026-01-15]
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ''

    @staticmethod
    def _looks_like_date(text):
        """判断文本是否像日期"""
        if not text or len(text) > 30:
            return False
        return bool(re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', text))

    @staticmethod
    def _parse_date(date_str: str):
        """解析日期字符串"""
        if not date_str:
            return None
        date_str = date_str.strip()
        for fmt in [
            '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
            '%Y年%m月%d日', '%Y年%m月%d',
            '%Y-%m-%d', '%Y%m%d',
            '%m月%d日',
        ]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # 尝试用正则提取
        match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', date_str)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
            except ValueError:
                pass
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
                'selectors': None,
            },
            {
                'name': '国家卫健委 - 政策文件',
                'url': 'https://www.gov.cn/fuwu/bm/wjw/index.htm',
                'source_type': 'web',
                'category': '卫健委',
                'crawl_method': 'get',
                'selectors': None,
            },
            {
                'name': '国家法律法规数据库',
                'url': 'https://flk.npc.gov.cn/',
                'source_type': 'web',
                'category': '法律法规',
                'crawl_method': 'get',
                'selectors': None,
            },
            {
                'name': '中国政府网 - 政策',
                'url': 'https://www.gov.cn/zhengce/',
                'source_type': 'web',
                'category': '法律法规',
                'crawl_method': 'get',
                'selectors': None,
            },
            {
                'name': '中国医院协会 - 行业动态',
                'url': 'https://www.cha.org.cn/',
                'source_type': 'web',
                'category': '行业动态',
                'crawl_method': 'get',
                'selectors': None,
            },
        ]

        for d in defaults:
            existing = MonitorSource.query.filter_by(url=d['url']).first()
            if not existing:
                source = MonitorSource(**d)
                self.db.add(source)
        self.db.commit()
        logger.info(f'已初始化 {len(defaults)} 个预置数据源')


class NewsCrawler:
    """行业资讯爬虫 - 专门用于爬取国内外档案行业资讯"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.policy_crawler = PolicyCrawler(db_session)
    
    def crawl_source(self, source):
        """爬取单个资讯数据源并保存到News表"""
        from models import MonitorSource, MonitorLog, News
        
        start_time = time.time()
        log_entry = MonitorLog(source_id=source.id, status='running')
        self.db.add(log_entry)
        self.db.flush()
        
        try:
            items = self.policy_crawler._fetch_items(source)
            log_entry.items_found = len(items)
            new_count = 0
            
            for item in items:
                content_text = f"{item.get('title', '')}{item.get('content', '')}"
                content_hash = compute_hash(content_text)
                
                # 检查是否已存在
                existing = News.query.filter_by(content_hash=content_hash).first()
                if existing:
                    continue
                
                # 确定国家和语言
                country = '中国'
                language = 'zh'
                if '国际' in source.category or 'ICA' in source.name or 'Archives' in source.name:
                    country = self._detect_country(source.name, source.url)
                    language = 'en' if country != '中国' else 'zh'
                
                news = News(
                    source_id=source.id,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    summary=item.get('summary', ''),
                    content=item.get('content', ''),
                    pub_date=item.get('pub_date'),
                    source_name=source.name,
                    country=country,
                    language=language,
                    tags=item.get('tags', source.category),
                    content_hash=content_hash,
                )
                self.db.add(news)
                new_count += 1
            
            log_entry.items_new = new_count
            log_entry.status = 'success'
            source.last_crawl_status = 'success'
            
            self.db.commit()
            logger.info(f"[{source.name}] 资讯抓取完成: 发现{len(items)}条, 新增{new_count}条")
            
        except Exception as e:
            log_entry.status = 'error'
            log_entry.error_message = str(e)
            source.last_crawl_status = 'error'
            self.db.commit()
            logger.error(f"[{source.name}] 资讯抓取失败: {e}")
        
        finally:
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            source.last_crawl_at = datetime.utcnow()
            self.db.commit()
    
    def crawl_all_enabled(self):
        """爬取所有启用的资讯数据源"""
        from models import MonitorSource
        # 只爬取资讯相关的数据源（可以根据category判断）
        sources = MonitorSource.query.filter_by(enabled=True).all()
        # 过滤出资讯数据源（可以根据名称或分类判断）
        news_sources = [s for s in sources if self._is_news_source(s)]
        
        for source in news_sources:
            try:
                self.crawl_source(source)
            except Exception as e:
                logger.error(f"资讯数据源 [{source.name}] 整体失败: {e}")
    
    def _is_news_source(self, source):
        """判断是否为资讯数据源"""
        # 根据分类或名称判断
        news_keywords = ['档案', 'archives', 'ica', 'news', '资讯', '动态']
        for keyword in news_keywords:
            if keyword.lower() in source.name.lower() or keyword in source.category:
                return True
        return False
    
    def _detect_country(self, source_name, source_url):
        """根据数据源名称或URL检测国家"""
        url_lower = source_url.lower()
        name_lower = source_name.lower()
        
        if 'china' in url_lower or 'saac' in url_lower or 'danganj' in url_lower:
            return '中国'
        elif 'archives.gov' in url_lower or 'nara' in url_lower or 'usa' in name_lower:
            return '美国'
        elif 'nationalarchives.gov.uk' in url_lower or 'uk' in name_lower:
            return '英国'
        elif 'naa.gov.au' in url_lower or 'australia' in name_lower:
            return '澳大利亚'
        elif 'bac-lac.gc.ca' in url_lower or 'canada' in name_lower:
            return '加拿大'
        elif 'ica.org' in url_lower:
            return '国际组织'
        else:
            return '其他'
