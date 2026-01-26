"""arXiv爬虫"""
import time
from typing import List, Optional
from datetime import datetime, timedelta
import arxiv
from crawlers.base_crawler import BaseCrawler, Article
from utils.logger import logger


class ArxivCrawler(BaseCrawler):
    """arXiv论文爬虫
    
    使用arXiv官方API获取论文
    """
    
    def __init__(self):
        super().__init__("arXiv")
        self.client = arxiv.Client()
    
    def crawl(
        self, 
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        max_results: int = 50,
        days_back: int = 7
    ) -> List[Article]:
        """
        从arXiv爬取论文
        
        Args:
            keywords: 搜索关键词列表
            categories: arXiv分类列表，如 ['cs.AI', 'cs.CV', 'cs.LG']
            max_results: 最大结果数
            days_back: 获取最近几天的论文
        
        Returns:
            List[Article]: 论文列表
        """
        if not keywords and not categories:
            logger.warning("未提供关键词或分类")
            return []
        
        all_articles = []
        
        # 构建查询
        query_parts = []
        
        # 添加关键词查询
        if keywords:
            # 使用 OR 连接关键词，搜索标题、摘要和关键词
            keyword_queries = []
            for keyword in keywords:
                keyword = keyword.strip()
                if keyword:
                    # 搜索标题、摘要
                    keyword_queries.append(f'(ti:"{keyword}" OR abs:"{keyword}")')
            
            if keyword_queries:
                query_parts.append(f"({' OR '.join(keyword_queries)})")
        
        # 添加分类查询
        if categories:
            cat_queries = [f'cat:{cat}' for cat in categories]
            query_parts.append(f"({' OR '.join(cat_queries)})")
        
        # 组合查询
        if len(query_parts) > 1:
            query = f"({' AND '.join(query_parts)})"
        else:
            query = query_parts[0] if query_parts else ""
        
        if not query:
            logger.warning("查询为空")
            return []
        
        logger.info(f"arXiv查询: {query}")
        logger.info(f"获取最近 {days_back} 天的论文，最多 {max_results} 篇")
        
        try:
            # 创建搜索对象
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,  # 按提交日期排序
                sort_order=arxiv.SortOrder.Descending  # 降序（最新的在前）
            )
            
            # 计算日期阈值
            date_threshold = datetime.now() - timedelta(days=days_back)
            
            # 获取结果
            count = 0
            for result in self.client.results(search):
                # 检查日期
                if result.published < date_threshold:
                    logger.debug(f"论文 {result.title} 发布日期早于阈值，跳过")
                    continue
                
                # 转换为Article对象
                article = self._convert_to_article(result)
                if article:
                    all_articles.append(article)
                    count += 1
                    logger.debug(f"获取论文 [{count}]: {article.title}")
                
                # 避免请求过快
                time.sleep(0.2)
            
            logger.info(f"从arXiv获取 {len(all_articles)} 篇论文")
            
        except Exception as e:
            logger.error(f"arXiv爬取失败: {e}", exc_info=True)
        
        return all_articles
    
    def _convert_to_article(self, result: arxiv.Result) -> Optional[Article]:
        """将arXiv结果转换为Article对象"""
        try:
            # 提取作者
            authors = ", ".join([author.name for author in result.authors])
            
            # 提取分类
            categories = result.categories
            
            # 构建内容：摘要 + 其他信息
            content_parts = [
                f"## 摘要\n{result.summary}",
                f"\n## 作者\n{authors}",
                f"\n## 分类\n{', '.join(categories)}",
            ]
            
            if result.comment:
                content_parts.append(f"\n## 备注\n{result.comment}")
            
            content = "\n".join(content_parts)
            
            article = Article(
                title=result.title,
                content=content,
                url=result.entry_id,
                source=self.source_name,
                publish_time=result.published,
                author=authors,
                tags=categories
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"转换arXiv结果失败: {e}")
            return None
    
    def crawl_by_categories(
        self, 
        categories: List[str], 
        max_results_per_category: int = 20,
        days_back: int = 7
    ) -> List[Article]:
        """按分类爬取论文"""
        all_articles = []
        
        for category in categories:
            logger.info(f"正在爬取分类: {category}")
            
            query = f"cat:{category}"
            
            try:
                search = arxiv.Search(
                    query=query,
                    max_results=max_results_per_category,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending
                )
                
                date_threshold = datetime.now() - timedelta(days=days_back)
                
                for result in self.client.results(search):
                    if result.published < date_threshold:
                        continue
                    
                    article = self._convert_to_article(result)
                    if article:
                        all_articles.append(article)
                
                logger.info(f"从分类 {category} 获取 {len(all_articles)} 篇论文")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"爬取分类 {category} 失败: {e}")
                continue
        
        return all_articles
