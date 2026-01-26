"""测试脚本 - 测试单个关键词"""
from crawlers.arxiv_crawler import ArxivCrawler
from writers.summary_writer import SummaryWriter
from config import ARXIV_CATEGORIES, DEEPSEEK_API_KEY
from utils.logger import logger
from datetime import datetime

def test_single_keyword():
    """测试单个关键词的完整流程"""
    
    # 测试关键词
    test_keyword = "大模型"
    
    logger.info("=" * 80)
    logger.info(f"测试关键词: {test_keyword}")
    logger.info("=" * 80)
    
    # 1. 初始化爬虫
    logger.info("\n[步骤 1] 初始化爬虫...")
    crawler = ArxivCrawler(download_dir="data/papers_test")
    
    # 2. 爬取论文
    logger.info(f"\n[步骤 2] 爬取 [{test_keyword}] 相关论文...")
    articles = crawler.crawl_by_keyword(
        keyword=test_keyword,
        categories=ARXIV_CATEGORIES,
        max_results=3,  # 测试只爬3篇
        date_filter="7",  # 最近7天
        download_pdf=True
    )
    
    if not articles:
        logger.warning("未获取到论文")
        return
    
    logger.info(f"获取 {len(articles)} 篇论文")
    
    # 3. 显示论文信息
    logger.info(f"\n[步骤 3] 论文列表:")
    for idx, article in enumerate(articles, 1):
        logger.info(f"\n{idx}. {article.title}")
        logger.info(f"   作者: {article.author}")
        logger.info(f"   时间: {article.publish_time.strftime('%Y-%m-%d')}")
        logger.info(f"   链接: {article.url}")
        if hasattr(article, 'pdf_path') and article.pdf_path:
            logger.info(f"   PDF: {article.pdf_path}")
    
    # 4. 生成总结
    if DEEPSEEK_API_KEY:
        logger.info(f"\n[步骤 4] 生成总结...")
        writer = SummaryWriter()
        summary = writer.generate_keyword_summary(test_keyword, articles)
        
        # 5. 保存总结
        logger.info(f"\n[步骤 5] 保存总结...")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"test_summary_{test_keyword}_{date_str}.md"
        filepath = writer.save_summary(summary, filename)
        logger.info(f"总结已保存: {filepath}")
    else:
        logger.warning("\n未配置 DEEPSEEK_API_KEY，跳过总结生成")
    
    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)

if __name__ == "__main__":
    test_single_keyword()
