"""主程序入口"""
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    WECHAT_ACCOUNTS, ARCHIVE_URLS, KEYWORDS,
    DEEPSEEK_API_KEY, ENABLE_ARXIV, ARXIV_CATEGORIES, 
    ARXIV_MAX_RESULTS, ARXIV_DAYS_BACK, FILTER_DAYS_BACK
)
from crawlers.wechat_crawler import WeChatCrawler
from crawlers.archive_crawler import ArchiveCrawler
from crawlers.arxiv_crawler import ArxivCrawler
from processors.integrator import ContentIntegrator
from processors.content_filter import ContentFilter
from rag.vector_store import VectorStore
from rag.retriever import Retriever
from writers.summary_writer import SummaryWriter
from utils.logger import logger


class DailySummaryAgent:
    """每日总结Agent"""
    
    def __init__(self):
        self.logger = logger.bind(module="main_agent")
        
        # 初始化组件
        self.wechat_crawler = WeChatCrawler()
        self.archive_crawler = ArchiveCrawler()
        self.arxiv_crawler = ArxivCrawler()
        self.integrator = ContentIntegrator()
        self.content_filter = ContentFilter()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store)
        self.summary_writer = SummaryWriter()
        
        self.logger.info("Daily Summary Agent 初始化完成")
    
    def run(self, use_rag: bool = True):
        """运行Agent"""
        self.logger.info("=" * 60)
        self.logger.info("开始执行每日总结任务")
        self.logger.info("=" * 60)
        
        try:
            # 1. 爬取数据
            self.logger.info("\n[步骤 1/6] 开始爬取数据...")
            all_articles = []
            
            # 微信公众号爬取
            if WECHAT_ACCOUNTS:
                self.logger.info(f"爬取微信公众号: {WECHAT_ACCOUNTS}")
                # 注意：这里需要提供RSS URL或使用其他方法
                # wechat_articles = self.wechat_crawler.crawl(account_names=WECHAT_ACCOUNTS)
                # all_articles.extend(wechat_articles)
                self.logger.warning("微信公众号爬取需要配置RSS URL或使用其他方法")
            else:
                self.logger.info("未配置微信公众号账号，跳过微信公众号爬取")
            
            # arXiv爬取
            if ENABLE_ARXIV:
                self.logger.info("=" * 60)
                self.logger.info("开始爬取arXiv论文")
                self.logger.info(f"关键词: {KEYWORDS}")
                self.logger.info(f"分类: {ARXIV_CATEGORIES}")
                self.logger.info("=" * 60)
                try:
                    arxiv_articles = self.arxiv_crawler.crawl(
                        keywords=KEYWORDS,
                        categories=ARXIV_CATEGORIES,
                        max_results=ARXIV_MAX_RESULTS,
                        days_back=ARXIV_DAYS_BACK
                    )
                    all_articles.extend(arxiv_articles)
                    self.logger.info(f"从arXiv获取 {len(arxiv_articles)} 篇论文")
                except Exception as e:
                    self.logger.error(f"arXiv爬取失败: {e}", exc_info=True)
            else:
                self.logger.info("arXiv爬取已禁用")
            
            # Archive爬取
            if ARCHIVE_URLS:
                self.logger.info(f"爬取Archive网站: {ARCHIVE_URLS}")
                try:
                    archive_articles = self.archive_crawler.crawl(urls=ARCHIVE_URLS)
                    all_articles.extend(archive_articles)
                    self.logger.info(f"从Archive网站获取 {len(archive_articles)} 篇文章")
                except Exception as e:
                    self.logger.error(f"Archive爬取失败: {e}", exc_info=True)
            else:
                self.logger.info("未配置ARCHIVE_URLS，跳过Archive爬取")
            
            if not all_articles:
                self.logger.warning("=" * 60)
                self.logger.warning("未获取到任何文章！")
                self.logger.warning("请检查以下配置：")
                self.logger.warning("  1. ENABLE_ARXIV 是否启用")
                self.logger.warning("  2. KEYWORDS 和 ARXIV_CATEGORIES 是否已配置")
                self.logger.warning("  3. ARCHIVE_URLS 是否已配置且可访问")
                self.logger.warning("  4. 网络连接是否正常")
                self.logger.warning("=" * 60)
                return
            
            self.logger.info(f"共爬取 {len(all_articles)} 篇文章")
            
            # 2. 内容过滤
            self.logger.info("\n[步骤 2/6] 内容过滤...")
            filtered_articles = self.content_filter.filter_articles(all_articles)
            
            # 清理内容
            filtered_articles = [self.content_filter.clean_content(article) for article in filtered_articles]
            
            # 3. 信息整合
            self.logger.info("\n[步骤 3/6] 信息整合...")
            integrated_data = self.integrator.integrate(filtered_articles, keywords=KEYWORDS, days_back=FILTER_DAYS_BACK)
            
            articles = integrated_data["articles"]
            categorized = integrated_data["categorized"]
            stats = integrated_data["stats"]
            
            if not articles:
                self.logger.warning("整合后没有符合条件的文章")
                return
            
            # 4. 添加到向量数据库
            self.logger.info("\n[步骤 4/6] 添加到向量数据库...")
            self.vector_store.add_articles(articles)
            
            # 5. 生成总结
            self.logger.info("\n[步骤 5/6] 生成总结...")
            if use_rag and DEEPSEEK_API_KEY:
                # 使用RAG生成总结
                summary = self.summary_writer.write_with_rag(
                    self.retriever,
                    query="今日AI、大模型、计算机视觉领域的重要内容和趋势",
                    top_k=15
                )
            else:
                # 直接生成总结
                summary = self.summary_writer.generate_summary(
                    articles=articles,
                    categories=categorized,
                    stats=stats
                )
            
            # 6. 保存总结
            self.logger.info("\n[步骤 6/6] 保存总结...")
            filepath = self.summary_writer.save_summary(summary)
            
            self.logger.info("=" * 60)
            self.logger.info("每日总结任务完成！")
            self.logger.info(f"总结文件: {filepath}")
            self.logger.info("=" * 60)
            
            # 打印统计信息
            self.logger.info(f"\n统计信息:")
            self.logger.info(f"  - 总文章数: {stats['total']}")
            self.logger.info(f"  - 去重后: {stats['unique']}")
            self.logger.info(f"  - 最近{FILTER_DAYS_BACK}天文章: {stats['recent']}")
            self.logger.info(f"  - 分类统计: {stats['by_category']}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"执行任务时出错: {e}", exc_info=True)
            raise


def main():
    """主函数"""
    agent = DailySummaryAgent()
    agent.run(use_rag=True)


if __name__ == "__main__":
    main()
