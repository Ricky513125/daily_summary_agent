"""主程序入口"""
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    WECHAT_ACCOUNTS, ARCHIVE_URLS, KEYWORDS,
    DEEPSEEK_API_KEY
)
from crawlers.wechat_crawler import WeChatCrawler
from crawlers.archive_crawler import ArchiveCrawler
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
                self.logger.info("爬取微信公众号...")
                # 注意：这里需要提供RSS URL或使用其他方法
                # wechat_articles = self.wechat_crawler.crawl(account_names=WECHAT_ACCOUNTS)
                # all_articles.extend(wechat_articles)
                self.logger.warning("微信公众号爬取需要配置RSS URL或使用其他方法")
            
            # Archive爬取
            if ARCHIVE_URLS:
                self.logger.info("爬取Archive网站...")
                archive_articles = self.archive_crawler.crawl(urls=ARCHIVE_URLS)
                all_articles.extend(archive_articles)
            
            if not all_articles:
                self.logger.warning("未获取到任何文章，请检查配置")
                return
            
            self.logger.info(f"共爬取 {len(all_articles)} 篇文章")
            
            # 2. 内容过滤
            self.logger.info("\n[步骤 2/6] 内容过滤...")
            filtered_articles = self.content_filter.filter_articles(all_articles)
            
            # 清理内容
            filtered_articles = [self.content_filter.clean_content(article) for article in filtered_articles]
            
            # 3. 信息整合
            self.logger.info("\n[步骤 3/6] 信息整合...")
            integrated_data = self.integrator.integrate(filtered_articles, keywords=KEYWORDS)
            
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
            self.logger.info(f"  - 今日文章: {stats['today']}")
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
