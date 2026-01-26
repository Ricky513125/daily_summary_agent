"""微信公众号爬虫"""
import re
import time
from typing import List, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from crawlers.base_crawler import BaseCrawler, Article
from config import CRAWL_TIMEOUT, MAX_ARTICLES_PER_SOURCE
from utils.logger import logger


class WeChatCrawler(BaseCrawler):
    """微信公众号爬虫
    
    注意: 微信公众号有反爬机制，实际使用时可能需要：
    1. 使用selenium/playwright模拟浏览器
    2. 使用第三方API服务（如搜狗微信搜索）
    3. 使用RSS订阅（如果公众号提供）
    """
    
    def __init__(self):
        super().__init__("微信公众号")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def crawl_from_rss(self, rss_url: str) -> List[Article]:
        """从RSS订阅爬取（如果公众号提供RSS）"""
        import feedparser
        
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            
            for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
                try:
                    # 解析发布时间
                    publish_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        publish_time = datetime(*entry.published_parsed[:6])
                    
                    article = Article(
                        title=entry.get('title', ''),
                        content=entry.get('summary', ''),
                        url=entry.get('link', ''),
                        source=self.source_name,
                        publish_time=publish_time,
                        author=entry.get('author', '')
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"解析RSS条目失败: {e}")
                    continue
            
            logger.info(f"从RSS获取 {len(articles)} 篇文章")
            return articles
        except Exception as e:
            logger.error(f"RSS爬取失败: {e}")
            return []
    
    def crawl_from_sogou(self, account_name: str) -> List[Article]:
        """从搜狗微信搜索爬取（示例实现）"""
        # 注意：搜狗微信搜索也有反爬，这里提供基础框架
        articles = []
        try:
            # 搜狗微信搜索URL
            search_url = f"https://weixin.sogou.com/weixin?type=1&query={account_name}"
            
            response = self.session.get(search_url, timeout=CRAWL_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # 这里需要根据实际HTML结构解析
            # 由于反爬机制，实际实现可能需要selenium
            
            logger.warning("搜狗微信搜索需要更复杂的实现（可能需要selenium）")
            return articles
        except Exception as e:
            logger.error(f"搜狗微信搜索失败: {e}")
            return []
    
    def crawl(self, rss_urls: Optional[List[str]] = None, account_names: Optional[List[str]] = None) -> List[Article]:
        """
        爬取微信公众号文章
        
        Args:
            rss_urls: RSS订阅URL列表
            account_names: 公众号名称列表（用于搜狗搜索）
        
        Returns:
            List[Article]: 文章列表
        """
        all_articles = []
        
        # 从RSS爬取
        if rss_urls:
            for rss_url in rss_urls:
                articles = self.crawl_from_rss(rss_url)
                all_articles.extend(articles)
                time.sleep(1)  # 避免请求过快
        
        # 从搜狗搜索爬取（如果提供）
        if account_names:
            for account in account_names:
                articles = self.crawl_from_sogou(account)
                all_articles.extend(articles)
                time.sleep(2)  # 避免请求过快
        
        logger.info(f"微信公众号爬虫共获取 {len(all_articles)} 篇文章")
        return all_articles
