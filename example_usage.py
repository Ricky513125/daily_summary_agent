"""使用示例"""
from main import DailySummaryAgent
from utils.logger import logger


def example_basic():
    """基础使用示例"""
    agent = DailySummaryAgent()
    agent.run(use_rag=False)


def example_with_rag():
    """使用RAG的示例"""
    agent = DailySummaryAgent()
    agent.run(use_rag=True)


def example_custom_crawl():
    """自定义爬取示例"""
    from crawlers.archive_crawler import ArchiveCrawler
    from crawlers.wechat_crawler import WeChatCrawler
    
    # 爬取特定Archive网站
    archive_crawler = ArchiveCrawler()
    articles = archive_crawler.crawl(urls=["https://example.com/archive"])
    
    logger.info(f"获取到 {len(articles)} 篇文章")
    for article in articles[:5]:
        logger.info(f"- {article.title}")


def example_rag_search():
    """RAG搜索示例"""
    from rag.vector_store import VectorStore
    from rag.retriever import Retriever
    
    vector_store = VectorStore()
    retriever = Retriever(vector_store)
    
    # 搜索相关内容
    results = retriever.retrieve("大模型的最新进展", top_k=5)
    
    for result in results:
        logger.info(f"标题: {result['metadata'].get('title', 'N/A')}")
        logger.info(f"内容: {result['content'][:100]}...")
        logger.info("-" * 50)


if __name__ == "__main__":
    # 运行基础示例
    example_basic()
    
    # 或者运行RAG示例
    # example_with_rag()
