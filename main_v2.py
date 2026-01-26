"""主程序入口 - 按关键词分别处理版本"""
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    KEYWORDS, DEEPSEEK_API_KEY, ENABLE_ARXIV, ARXIV_CATEGORIES, 
    ARXIV_MAX_RESULTS_PER_KEYWORD, ARXIV_DATE_FILTER, ARXIV_DOWNLOAD_PDF,
    ARXIV_PAPERS_DIR, OUTPUT_DIR
)
from crawlers.arxiv_crawler import ArxivCrawler
from writers.summary_writer import SummaryWriter
from utils.logger import logger


class DailySummaryAgentV2:
    """每日总结Agent - 按关键词分别处理版本"""
    
    def __init__(self):
        self.logger = logger.bind(module="main_agent_v2")
        
        # 初始化组件
        self.arxiv_crawler = ArxivCrawler(download_dir=str(ARXIV_PAPERS_DIR))
        self.summary_writer = SummaryWriter()
        
        self.logger.info("Daily Summary Agent V2 初始化完成")
    
    def run(self):
        """运行Agent - 为每个关键词单独处理"""
        self.logger.info("=" * 80)
        self.logger.info("开始执行每日总结任务 (按关键词分别处理)")
        self.logger.info("=" * 80)
        
        if not ENABLE_ARXIV:
            self.logger.warning("arXiv爬取未启用")
            return
        
        if not KEYWORDS:
            self.logger.warning("未配置关键词")
            return
        
        try:
            total_articles = 0
            total_summaries = 0
            
            # 为每个关键词单独处理
            for idx, keyword in enumerate(KEYWORDS, 1):
                keyword = keyword.strip()
                if not keyword:
                    continue
                
                self.logger.info("\n" + "=" * 80)
                self.logger.info(f"[{idx}/{len(KEYWORDS)}] 处理关键词: {keyword}")
                self.logger.info("=" * 80)
                
                try:
                    # 1. 爬取该关键词的论文
                    self.logger.info(f"\n[步骤 1/3] 爬取 [{keyword}] 相关论文...")
                    articles = self.arxiv_crawler.crawl_by_keyword(
                        keyword=keyword,
                        categories=ARXIV_CATEGORIES,
                        max_results=ARXIV_MAX_RESULTS_PER_KEYWORD,
                        date_filter=ARXIV_DATE_FILTER,
                        download_pdf=ARXIV_DOWNLOAD_PDF
                    )
                    
                    if not articles:
                        self.logger.warning(f"[{keyword}] 未获取到论文")
                        continue
                    
                    self.logger.info(f"[{keyword}] 获取 {len(articles)} 篇论文")
                    total_articles += len(articles)
                    
                    # 2. 生成该关键词的总结
                    self.logger.info(f"\n[步骤 2/3] 生成 [{keyword}] 总结...")
                    if DEEPSEEK_API_KEY:
                        summary = self.summary_writer.generate_keyword_summary(
                            keyword=keyword,
                            articles=articles
                        )
                    else:
                        # 如果没有API密钥，生成简单的论文列表
                        summary = self._generate_simple_summary(keyword, articles)
                    
                    # 3. 保存该关键词的总结
                    self.logger.info(f"\n[步骤 3/3] 保存 [{keyword}] 总结...")
                    date_str = datetime.now().strftime("%Y%m%d")
                    filename = f"summary_{keyword}_{date_str}.md"
                    # 清理文件名中的特殊字符
                    filename = filename.replace("/", "_").replace(" ", "_").replace("\\", "_")
                    
                    filepath = self.summary_writer.save_summary(summary, filename)
                    total_summaries += 1
                    
                    self.logger.info(f"[{keyword}] 总结已保存: {filepath}")
                    
                except Exception as e:
                    self.logger.error(f"[{keyword}] 处理失败: {e}", exc_info=True)
                    continue
            
            # 4. 生成汇总报告
            self.logger.info("\n" + "=" * 80)
            self.logger.info("任务完成！")
            self.logger.info("=" * 80)
            self.logger.info(f"总关键词数: {len(KEYWORDS)}")
            self.logger.info(f"总论文数: {total_articles}")
            self.logger.info(f"生成总结数: {total_summaries}")
            self.logger.info(f"论文保存目录: {ARXIV_PAPERS_DIR}")
            self.logger.info(f"总结保存目录: {OUTPUT_DIR}")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"执行任务时出错: {e}", exc_info=True)
            raise
    
    def _generate_simple_summary(self, keyword: str, articles: list) -> str:
        """生成简单的论文列表（当没有API密钥时）"""
        lines = [
            f"# {keyword} - 论文列表",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n共 {len(articles)} 篇论文\n",
            "---\n"
        ]
        
        for idx, article in enumerate(articles, 1):
            lines.append(f"\n## {idx}. {article.title}\n")
            lines.append(f"**作者**: {article.author}\n")
            lines.append(f"**发布时间**: {article.publish_time.strftime('%Y-%m-%d')}\n")
            lines.append(f"**链接**: {article.url}\n")
            if hasattr(article, 'pdf_path') and article.pdf_path:
                lines.append(f"**PDF**: {article.pdf_path}\n")
            lines.append(f"\n**摘要**:\n{article.content}\n")
            lines.append("\n---\n")
        
        return "\n".join(lines)


def main():
    """主函数"""
    agent = DailySummaryAgentV2()
    agent.run()


if __name__ == "__main__":
    main()
