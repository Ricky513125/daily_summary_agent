"""基础爬虫类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from utils.logger import logger


class Article:
    """文章数据类"""
    def __init__(
        self,
        title: str,
        content: str,
        url: str,
        source: str,
        publish_time: Optional[datetime] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        self.title = title
        self.content = content
        self.url = url
        self.source = source
        self.publish_time = publish_time or datetime.now()
        self.author = author
        self.tags = tags or []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "author": self.author,
            "tags": self.tags
        }
    
    def __repr__(self):
        return f"Article(title='{self.title[:50]}...', source='{self.source}')"


class BaseCrawler(ABC):
    """基础爬虫类"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logger.bind(source=source_name)
    
    @abstractmethod
    def crawl(self, **kwargs) -> List[Article]:
        """
        爬取文章
        
        Returns:
            List[Article]: 文章列表
        """
        pass
    
    def filter_by_keywords(self, articles: List[Article], keywords: List[str]) -> List[Article]:
        """根据关键词过滤文章"""
        if not keywords:
            return articles
        
        filtered = []
        for article in articles:
            # 检查标题和内容中是否包含关键词
            text = f"{article.title} {article.content}".lower()
            if any(keyword.lower() in text for keyword in keywords):
                filtered.append(article)
        
        self.logger.info(f"过滤后剩余 {len(filtered)}/{len(articles)} 篇文章")
        return filtered
