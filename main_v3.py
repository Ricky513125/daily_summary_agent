"""主程序入口 V3 - 看2天前的文章，按日期组织文件夹，使用阿里千问"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    KEYWORDS, DASHSCOPE_API_KEY, ENABLE_ARXIV, ARXIV_CATEGORIES, 
    ARXIV_MAX_RESULTS_PER_KEYWORD, ARXIV_DOWNLOAD_PDF,
    ARXIV_PAPERS_DIR, OUTPUT_DIR, ARXIV_DAYS_AGO,
    EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAILS
)
from crawlers.arxiv_crawler import ArxivCrawler
from writers.summary_writer_qwen import SummaryWriterQwen
from utils.summary_aggregator import SummaryAggregator
from utils.email_sender import EmailSender, markdown_to_html
from utils.logger import logger


class DailySummaryAgentV3:
    """每日总结Agent V3 - 看N天前的文章，按日期组织"""
    
    def __init__(self, days_ago: int = None):
        """
        初始化
        
        Args:
            days_ago: 看几天前的文章，默认从配置读取
        """
        self.logger = logger.bind(module="main_agent_v3")
        self.days_ago = days_ago if days_ago is not None else ARXIV_DAYS_AGO
        
        # 计算目标日期（N天前）
        self.target_date = datetime.now(timezone.utc) - timedelta(days=self.days_ago)
        self.target_date_str = self.target_date.strftime("%Y%m%d")  # YYYYMMDD
        self.target_date_readable = self.target_date.strftime("%Y-%m-%d")  # YYYY-MM-DD
        
        # 创建日期目录
        self.papers_dir = Path(ARXIV_PAPERS_DIR) / self.target_date_str
        self.output_dir = Path(OUTPUT_DIR) / self.target_date_str
        
        # 初始化组件
        self.arxiv_crawler = ArxivCrawler(download_dir=str(self.papers_dir))
        self.summary_writer = SummaryWriterQwen()
        self.aggregator = SummaryAggregator()
        
        # 初始化邮件发送器
        if EMAIL_ENABLED and SENDER_EMAIL and SENDER_PASSWORD:
            self.email_sender = EmailSender(
                smtp_server=SMTP_SERVER,
                smtp_port=SMTP_PORT,
                sender_email=SENDER_EMAIL,
                sender_password=SENDER_PASSWORD
            )
            self.email_enabled = True
        else:
            self.email_sender = None
            self.email_enabled = False
        
        self.logger.info(f"Daily Summary Agent V3 初始化完成")
        self.logger.info(f"目标日期: {self.target_date_readable} ({self.days_ago}天前)")
        self.logger.info(f"论文保存: {self.papers_dir}")
        self.logger.info(f"总结保存: {self.output_dir}")
    
    def run(self):
        """运行Agent - 为每个关键词单独处理"""
        self.logger.info("=" * 80)
        self.logger.info("开始执行每日总结任务 V3")
        self.logger.info(f"查看日期: {self.target_date_readable} ({self.days_ago}天前)")
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
                    # 1. 爬取该关键词在目标日期的论文
                    self.logger.info(f"\n[步骤 1/3] 爬取 [{keyword}] 在 {self.target_date_readable} 发布的论文...")
                    articles = self._crawl_keyword_papers(keyword)
                    
                    if not articles:
                        self.logger.warning(f"[{keyword}] 在 {self.target_date_readable} 未获取到论文")
                        continue
                    
                    self.logger.info(f"[{keyword}] 获取 {len(articles)} 篇论文")
                    total_articles += len(articles)
                    
                    # 2. 生成该关键词的总结
                    self.logger.info(f"\n[步骤 2/3] 生成 [{keyword}] 总结...")
                    summary = self.summary_writer.generate_keyword_summary(
                        keyword=keyword,
                        articles=articles,
                        target_date=self.target_date_readable
                    )
                    
                    # 3. 保存该关键词的总结到日期目录
                    self.logger.info(f"\n[步骤 3/3] 保存 [{keyword}] 总结...")
                    filepath = self.summary_writer.save_summary(
                        summary=summary,
                        keyword=keyword,
                        date_str=self.target_date_str
                    )
                    total_summaries += 1
                    
                    self.logger.info(f"[{keyword}] 总结已保存: {filepath}")
                    
                except Exception as e:
                    self.logger.error(f"[{keyword}] 处理失败: {e}", exc_info=True)
                    continue
            
            # 4. 生成汇总报告
            self.logger.info("\n" + "=" * 80)
            self.logger.info("任务完成！")
            self.logger.info("=" * 80)
            self.logger.info(f"目标日期: {self.target_date_readable}")
            self.logger.info(f"总关键词数: {len(KEYWORDS)}")
            self.logger.info(f"总论文数: {total_articles}")
            self.logger.info(f"生成总结数: {total_summaries}")
            self.logger.info(f"论文保存目录: {self.papers_dir}")
            self.logger.info(f"总结保存目录: {self.output_dir}")
            self.logger.info("=" * 80)
            
            # 生成索引文件
            self._generate_index()
            
            # 5. 汇总所有总结
            if total_summaries > 0:
                self.logger.info("\n" + "=" * 80)
                self.logger.info("汇总总结文档...")
                self.logger.info("=" * 80)
                
                aggregated_file = self._aggregate_and_send(total_summaries)
                
                if aggregated_file:
                    self.logger.info(f"汇总文档: {aggregated_file}")
            
        except Exception as e:
            self.logger.error(f"执行任务时出错: {e}", exc_info=True)
            raise
    
    def _crawl_keyword_papers(self, keyword: str) -> list:
        """爬取指定关键词在目标日期的论文"""
        # 计算目标日期的开始和结束时间
        start_time = self.target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        self.logger.info(f"[{keyword}] 查找时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 使用 crawl_by_keyword 方法，但需要自定义日期过滤
        # 先搜索更大范围，然后精确过滤
        try:
            search_query = f'(ti:"{keyword}" OR abs:"{keyword}")'
            if ARXIV_CATEGORIES:
                cat_queries = [f'cat:{cat}' for cat in ARXIV_CATEGORIES]
                search_query += f" AND ({' OR '.join(cat_queries)})"
            
            import arxiv
            search = arxiv.Search(
                query=search_query,
                max_results=ARXIV_MAX_RESULTS_PER_KEYWORD * 5,  # 搜索更多以便过滤
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            articles = []
            for result in self.arxiv_crawler.client.results(search):
                # 精确匹配目标日期
                if start_time <= result.published < end_time:
                    article = self.arxiv_crawler._convert_to_article(result, keyword)
                    if article:
                        # 下载PDF到日期/关键词目录
                        if ARXIV_DOWNLOAD_PDF:
                            pdf_path = self.arxiv_crawler._download_pdf(result, keyword)
                            if pdf_path:
                                article.pdf_path = pdf_path
                        
                        articles.append(article)
                        self.logger.info(f"[{keyword}] 找到论文: {article.title[:60]}...")
                        
                        if len(articles) >= ARXIV_MAX_RESULTS_PER_KEYWORD:
                            break
                
                # 如果论文日期太早，停止搜索
                if result.published < start_time - timedelta(days=2):
                    break
            
            return articles
            
        except Exception as e:
            self.logger.error(f"[{keyword}] 爬取失败: {e}", exc_info=True)
            return []
    
    def _generate_index(self):
        """生成索引文件"""
        try:
            index_path = self.output_dir / "README.md"
            
            lines = [
                f"# {self.target_date_readable} 论文总结索引",
                f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"\n## 关键词列表\n"
            ]
            
            # 列出所有生成的总结文件
            for keyword in KEYWORDS:
                keyword = keyword.strip()
                if not keyword:
                    continue
                
                safe_keyword = keyword.replace("/", "_").replace(" ", "_").replace("\\", "_")
                summary_file = f"summary_{safe_keyword}.md"
                summary_path = self.output_dir / summary_file
                
                if summary_path.exists():
                    lines.append(f"- [{keyword}](./{summary_file})")
            
            lines.append(f"\n## 论文PDF")
            lines.append(f"\nPDF文件保存在: `{self.papers_dir.relative_to(Path.cwd())}/`")
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            self.logger.info(f"索引文件已生成: {index_path}")
            
        except Exception as e:
            self.logger.error(f"生成索引文件失败: {e}")
    
    def _aggregate_and_send(self, total_summaries: int) -> Path:
        """汇总总结并发送邮件"""
        try:
            # 1. 生成汇总文档
            aggregated_file = self.output_dir / f"汇总总结_{self.target_date_str}.md"
            self.aggregator.aggregate_summaries(
                summary_dir=self.output_dir,
                output_path=aggregated_file,
                date_str=self.target_date_str,
                keywords=KEYWORDS
            )
            
            # 2. 发送邮件
            if self.email_enabled and RECEIVER_EMAILS:
                self.logger.info("发送邮件...")
                
                # 读取汇总内容
                with open(aggregated_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 转换为HTML
                html_content = markdown_to_html(content)
                
                # 发送邮件
                date_readable = datetime.strptime(self.target_date_str, "%Y%m%d").strftime("%Y年%m月%d日")
                subject = f"【AI论文每日总结】{date_readable} - {total_summaries}个关键词"
                
                success = self.email_sender.send_summary(
                    receiver_emails=RECEIVER_EMAILS,
                    subject=subject,
                    content=html_content,
                    attachments=[str(aggregated_file)]
                )
                
                if success:
                    self.logger.info(f"邮件发送成功: {RECEIVER_EMAILS}")
                else:
                    self.logger.warning("邮件发送失败")
            else:
                if not self.email_enabled:
                    self.logger.info("邮件功能未启用")
                else:
                    self.logger.warning("未配置收件人邮箱")
            
            return aggregated_file
            
        except Exception as e:
            self.logger.error(f"汇总和发送失败: {e}", exc_info=True)
            return None


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='每日AI总结Agent V3 - 看N天前的文章')
    parser.add_argument('--days-ago', type=int, help='查看几天前的文章（默认2天）')
    args = parser.parse_args()
    
    agent = DailySummaryAgentV3(days_ago=args.days_ago)
    agent.run()


if __name__ == "__main__":
    main()
