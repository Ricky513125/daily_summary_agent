"""内容过滤器"""
from typing import List
from crawlers.base_crawler import Article
from utils.logger import logger
import re


class ContentFilter:
    """内容过滤器"""
    
    def __init__(self, min_length: int = 100, max_length: int = 50000):
        self.min_length = min_length
        self.max_length = max_length
        self.logger = logger.bind(module="filter")
    
    def filter_articles(self, articles: List[Article]) -> List[Article]:
        """过滤文章"""
        filtered = []
        
        for article in articles:
            if self._is_valid(article):
                filtered.append(article)
            else:
                self.logger.debug(f"过滤文章: {article.title}")
        
        self.logger.info(f"过滤后剩余 {len(filtered)}/{len(articles)} 篇文章")
        return filtered
    
    def _is_valid(self, article: Article) -> bool:
        """检查文章是否有效"""
        # 检查内容长度
        content_length = len(article.content)
        if content_length < self.min_length or content_length > self.max_length:
            return False
        
        # 检查标题
        if not article.title or len(article.title.strip()) < 5:
            return False
        
        # 检查URL
        if not article.url or not article.url.startswith(('http://', 'https://')):
            return False
        
        # 检查是否包含过多广告或无效内容
        if self._contains_spam(article):
            return False
        
        return True
    
    def _contains_spam(self, article: Article) -> bool:
        """检查是否包含垃圾内容"""
        spam_patterns = [
            r'点击.*关注',
            r'扫码.*关注',
            r'广告.*投放',
            r'商务合作',
        ]
        
        text = f"{article.title} {article.content}"
        for pattern in spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def clean_content(self, article: Article) -> Article:
        """清理文章内容"""
        # 移除多余的空白字符
        article.content = re.sub(r'\s+', ' ', article.content).strip()
        
        # 移除HTML标签（如果有）
        article.content = re.sub(r'<[^>]+>', '', article.content)
        
        return article
