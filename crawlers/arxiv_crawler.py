"""arXiv爬虫"""
import time
import os
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
import arxiv
from crawlers.base_crawler import BaseCrawler, Article
from utils.logger import logger


class ArxivCrawler(BaseCrawler):
    """arXiv论文爬虫
    
    使用arXiv官方API获取论文
    """
    
    def __init__(self, download_dir: str = None):
        super().__init__("arXiv")
        self.client = arxiv.Client()
        self.download_dir = Path(download_dir) if download_dir else Path("data/papers")
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def crawl_by_keyword(
        self,
        keyword: str,
        categories: Optional[List[str]] = None,
        max_results: int = 10,
        date_filter: str = "yesterday",  # "yesterday", "today", or days_back
        download_pdf: bool = True
    ) -> List[Article]:
        """
        按单个关键词从arXiv爬取论文
        
        Args:
            keyword: 搜索关键词
            categories: arXiv分类列表，如 ['cs.AI', 'cs.CV', 'cs.LG']
            max_results: 最大结果数
            date_filter: 日期过滤，"yesterday"=昨天, "today"=今天
            download_pdf: 是否下载PDF
        
        Returns:
            List[Article]: 论文列表
        """
        if not keyword:
            logger.warning("未提供关键词")
            return []
        
        all_articles = []
        
        # 构建查询 - 只搜索单个关键词
        query_parts = []
        keyword = keyword.strip()
        query_parts.append(f'(ti:"{keyword}" OR abs:"{keyword}")')
        
        # 添加分类查询
        if categories:
            cat_queries = [f'cat:{cat}' for cat in categories]
            query_parts.append(f"({' OR '.join(cat_queries)})")
        
        # 组合查询
        if len(query_parts) > 1:
            query = f"({' AND '.join(query_parts)})"
        else:
            query = query_parts[0]
        
        logger.info(f"[{keyword}] arXiv查询: {query}")
        logger.info(f"[{keyword}] 日期过滤: {date_filter}，最多 {max_results} 篇")
        
        try:
            # 创建搜索对象 - 搜索更多结果以便过滤
            search = arxiv.Search(
                query=query,
                max_results=max_results * 3,  # 搜索3倍数量以便日期过滤
                sort_by=arxiv.SortCriterion.SubmittedDate,  # 按提交日期排序
                sort_order=arxiv.SortOrder.Descending  # 降序（最新的在前）
            )
            
            # 计算日期范围
            now = datetime.now(timezone.utc)
            if date_filter == "yesterday":
                # 昨天：从昨天0点到昨天23:59:59
                start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
                logger.info(f"[{keyword}] 查找昨天的论文: {start_date.date()}")
            elif date_filter == "today":
                # 今天：从今天0点到现在
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = now
                logger.info(f"[{keyword}] 查找今天的论文: {start_date.date()}")
            else:
                # 最近N天
                days = int(date_filter) if isinstance(date_filter, (int, str)) and str(date_filter).isdigit() else 7
                start_date = now - timedelta(days=days)
                end_date = now
                logger.info(f"[{keyword}] 查找最近{days}天的论文")
            
            # 获取结果
            count = 0
            for result in self.client.results(search):
                # 检查日期范围
                if result.published < start_date or result.published >= end_date:
                    continue
                
                # 转换为Article对象
                article = self._convert_to_article(result, keyword)
                if article:
                    # 下载PDF
                    if download_pdf:
                        pdf_path = self._download_pdf(result, keyword)
                        if pdf_path:
                            article.pdf_path = pdf_path
                    
                    all_articles.append(article)
                    count += 1
                    logger.info(f"[{keyword}] 获取论文 [{count}]: {article.title[:60]}...")
                    
                    # 达到目标数量就停止
                    if count >= max_results:
                        break
                
                # 避免请求过快
                time.sleep(0.3)
            
            logger.info(f"[{keyword}] 共获取 {len(all_articles)} 篇论文")
            
        except Exception as e:
            logger.error(f"[{keyword}] arXiv爬取失败: {e}", exc_info=True)
        
        return all_articles
    
    def _convert_to_article(self, result: arxiv.Result, keyword: str = "") -> Optional[Article]:
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
                f"\n## arXiv ID\n{result.get_short_id()}"
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
                tags=[keyword] if keyword else categories
            )
            
            # 添加额外属性
            article.arxiv_id = result.get_short_id()
            article.pdf_url = result.pdf_url
            article.keyword = keyword
            
            return article
            
        except Exception as e:
            logger.warning(f"转换arXiv结果失败: {e}")
            return None
    
    def _download_pdf(self, result: arxiv.Result, keyword: str) -> Optional[str]:
        """下载论文PDF"""
        try:
            # 创建关键词目录
            keyword_dir = self.download_dir / keyword.replace("/", "_").replace(" ", "_")
            keyword_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            arxiv_id = result.get_short_id().replace("/", "_")
            pdf_filename = f"{arxiv_id}.pdf"
            pdf_path = keyword_dir / pdf_filename
            
            # 如果已存在则跳过
            if pdf_path.exists():
                logger.debug(f"[{keyword}] PDF已存在: {pdf_filename}")
                return str(pdf_path)
            
            # 下载PDF
            logger.info(f"[{keyword}] 下载PDF: {pdf_filename}")
            result.download_pdf(dirpath=str(keyword_dir), filename=pdf_filename)
            
            return str(pdf_path)
            
        except Exception as e:
            logger.warning(f"[{keyword}] 下载PDF失败: {e}")
            return None
    
    def crawl(self, keywords: Optional[List[str]] = None, **kwargs) -> List[Article]:
        """
        实现抽象方法 crawl（为了兼容 BaseCrawler）
        
        Args:
            keywords: 关键词列表
            **kwargs: 其他参数
        
        Returns:
            List[Article]: 论文列表
        """
        if not keywords:
            logger.warning("未提供关键词")
            return []
        
        all_articles = []
        
        # 对每个关键词调用 crawl_by_keyword
        for keyword in keywords:
            articles = self.crawl_by_keyword(
                keyword=keyword,
                categories=kwargs.get('categories'),
                max_results=kwargs.get('max_results', 10),
                date_filter=kwargs.get('date_filter', 'yesterday'),
                download_pdf=kwargs.get('download_pdf', True)
            )
            all_articles.extend(articles)
        
        return all_articles
    
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
                
                date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
                
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
