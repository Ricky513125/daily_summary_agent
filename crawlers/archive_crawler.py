"""Archive爬虫"""
import time
from typing import List, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from crawlers.base_crawler import BaseCrawler, Article
from config import CRAWL_TIMEOUT, MAX_ARTICLES_PER_SOURCE
from utils.logger import logger


class ArchiveCrawler(BaseCrawler):
    """Archive网站爬虫
    
    支持多种Archive网站：
    - Internet Archive (archive.org)
    - 其他Archive网站
    """
    
    def __init__(self):
        super().__init__("Archive")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def crawl_internet_archive(self, url: str, max_pages: int = 5) -> List[Article]:
        """爬取Internet Archive"""
        articles = []
        try:
            # Internet Archive的API或网页爬取
            # 这里提供基础框架，实际需要根据具体网站结构调整
            response = self.session.get(url, timeout=CRAWL_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析文章列表（需要根据实际HTML结构调整）
            # 示例：查找文章链接
            article_links = soup.find_all('a', href=True)
            
            for link in article_links[:MAX_ARTICLES_PER_SOURCE]:
                try:
                    article_url = link.get('href', '')
                    if not article_url.startswith('http'):
                        article_url = url + article_url
                    
                    # 获取文章详情
                    article = self._fetch_article_detail(article_url)
                    if article:
                        articles.append(article)
                    
                    time.sleep(0.5)  # 避免请求过快
                except Exception as e:
                    logger.warning(f"获取文章详情失败: {e}")
                    continue
            
            logger.info(f"从Internet Archive获取 {len(articles)} 篇文章")
            return articles
        except Exception as e:
            logger.error(f"Internet Archive爬取失败: {e}")
            return []
    
    def _fetch_article_detail(self, url: str) -> Optional[Article]:
        """获取文章详情"""
        try:
            response = self.session.get(url, timeout=CRAWL_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = soup.find('title')
            title = title.text.strip() if title else "无标题"
            
            # 提取正文（需要根据实际网站结构调整）
            content = ""
            # 尝试多种常见的正文选择器
            for selector in ['article', '.content', '.post-content', 'main', 'body']:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break
            
            if not content:
                # 如果找不到，使用body的全部文本
                content = soup.get_text(strip=True)
            
            # 提取发布时间（如果存在）
            publish_time = None
            time_elem = soup.find('time')
            if time_elem and time_elem.get('datetime'):
                try:
                    publish_time = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            return Article(
                title=title,
                content=content[:5000],  # 限制内容长度
                url=url,
                source=self.source_name,
                publish_time=publish_time
            )
        except Exception as e:
            logger.warning(f"获取文章详情失败 {url}: {e}")
            return None
    
    def crawl(self, urls: Optional[List[str]] = None) -> List[Article]:
        """
        爬取Archive网站文章
        
        Args:
            urls: Archive网站URL列表
        
        Returns:
            List[Article]: 文章列表
        """
        if not urls:
            logger.warning("未提供Archive URL")
            return []
        
        all_articles = []
        
        for url in urls:
            try:
                if 'archive.org' in url:
                    articles = self.crawl_internet_archive(url)
                else:
                    # 通用Archive网站爬取
                    articles = self._crawl_generic_archive(url)
                
                all_articles.extend(articles)
                time.sleep(1)  # 避免请求过快
            except Exception as e:
                logger.error(f"爬取Archive URL失败 {url}: {e}")
                continue
        
        logger.info(f"Archive爬虫共获取 {len(all_articles)} 篇文章")
        return all_articles
    
    def _crawl_generic_archive(self, url: str) -> List[Article]:
        """通用Archive网站爬取"""
        articles = []
        try:
            response = self.session.get(url, timeout=CRAWL_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 通用解析逻辑（需要根据实际网站调整）
            # 这里提供一个基础框架
            article_links = soup.find_all('a', href=True)
            
            for link in article_links[:MAX_ARTICLES_PER_SOURCE]:
                try:
                    article_url = link.get('href', '')
                    if not article_url.startswith('http'):
                        article_url = url.rstrip('/') + '/' + article_url.lstrip('/')
                    
                    article = self._fetch_article_detail(article_url)
                    if article:
                        articles.append(article)
                    
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"获取文章失败: {e}")
                    continue
            
            return articles
        except Exception as e:
            logger.error(f"通用Archive爬取失败: {e}")
            return []
