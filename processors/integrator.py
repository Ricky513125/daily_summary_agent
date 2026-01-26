"""信息整合模块"""
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from crawlers.base_crawler import Article
from utils.logger import logger
import hashlib


class ContentIntegrator:
    """内容整合器"""
    
    def __init__(self):
        self.logger = logger.bind(module="integrator")
    
    def deduplicate(self, articles: List[Article]) -> List[Article]:
        """去重文章"""
        seen_hashes = set()
        unique_articles = []
        
        for article in articles:
            # 使用标题和URL生成哈希
            content_hash = self._generate_hash(article.title, article.url)
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_articles.append(article)
            else:
                self.logger.debug(f"发现重复文章: {article.title}")
        
        self.logger.info(f"去重后剩余 {len(unique_articles)}/{len(articles)} 篇文章")
        return unique_articles
    
    def _generate_hash(self, title: str, url: str) -> str:
        """生成内容哈希"""
        content = f"{title}{url}".lower().strip()
        return hashlib.md5(content.encode()).hexdigest()
    
    def categorize(self, articles: List[Article], keywords: List[str]) -> Dict[str, List[Article]]:
        """按关键词分类文章"""
        categories = defaultdict(list)
        
        for article in articles:
            text = f"{article.title} {article.content}".lower()
            
            # 找到匹配的关键词
            matched_keywords = [kw for kw in keywords if kw.lower() in text]
            
            if matched_keywords:
                # 使用第一个匹配的关键词作为分类
                category = matched_keywords[0]
                categories[category].append(article)
            else:
                categories["其他"].append(article)
        
        self.logger.info(f"文章分类完成: {dict(categories)}")
        return dict(categories)
    
    def filter_by_date(self, articles: List[Article], days_back: int = 7) -> List[Article]:
        """按日期过滤文章，保留最近N天的文章"""
        # 计算日期阈值（使用UTC时区）
        now = datetime.now(timezone.utc)
        date_threshold = now - timedelta(days=days_back)
        
        filtered = []
        for article in articles:
            if not article.publish_time:
                # 如果没有发布时间，默认保留
                filtered.append(article)
                continue
            
            # 确保 publish_time 有时区信息
            pub_time = article.publish_time
            if pub_time.tzinfo is None:
                # 如果没有时区信息，假设为UTC
                pub_time = pub_time.replace(tzinfo=timezone.utc)
            
            # 检查是否在时间范围内
            if pub_time >= date_threshold:
                filtered.append(article)
        
        self.logger.info(f"按日期过滤后剩余 {len(filtered)}/{len(articles)} 篇文章（最近{days_back}天）")
        return filtered
    
    def integrate(self, articles: List[Article], keywords: List[str] = None, days_back: int = 7) -> Dict:
        """整合所有文章"""
        # 去重
        unique_articles = self.deduplicate(articles)
        
        # 按日期过滤（保留最近N天的）
        recent_articles = self.filter_by_date(unique_articles, days_back=days_back)
        
        # 分类
        if keywords:
            categorized = self.categorize(recent_articles, keywords)
        else:
            categorized = {"全部": recent_articles}
        
        # 统计信息
        stats = {
            "total": len(articles),
            "unique": len(unique_articles),
            "recent": len(recent_articles),
            "by_category": {k: len(v) for k, v in categorized.items()}
        }
        
        self.logger.info(f"整合完成: {stats}")
        
        return {
            "articles": recent_articles,
            "categorized": categorized,
            "stats": stats
        }
