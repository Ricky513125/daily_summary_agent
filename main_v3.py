"""主程序入口 V3 - 看2天前的文章，按日期组织文件夹，使用阿里千问"""
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    KEYWORDS, DASHSCOPE_API_KEY, ENABLE_ARXIV, ARXIV_CATEGORIES, 
    ARXIV_MAX_RESULTS_PER_KEYWORD, ARXIV_DOWNLOAD_PDF,
    ARXIV_PAPERS_DIR, OUTPUT_DIR, ARXIV_DAYS_AGO,
    EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAILS,
    DEDUP_ENABLED, DEDUP_CACHE_PATH, DEDUP_RETENTION_DAYS,
    ARCHIVE_URLS, V3_BATCH_SIZE, DATA_DIR
)
from crawlers.arxiv_crawler import ArxivCrawler
from crawlers.archive_crawler import ArchiveCrawler
from writers.summary_writer_qwen import SummaryWriterQwen
from utils.summary_aggregator import SummaryAggregator
from utils.email_sender import EmailSender, markdown_to_html
from utils.logger import logger
from utils.paper_deduper import PersistentPaperDeduper


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
        self.archive_crawler = ArchiveCrawler()
        self.summary_writer = SummaryWriterQwen()
        self.aggregator = SummaryAggregator()

        # 初始化去重器（避免跨关键词/跨天重复分析同一篇）
        self.dedup_enabled = bool(DEDUP_ENABLED)
        self.deduper = None
        if self.dedup_enabled:
            try:
                self.deduper = PersistentPaperDeduper(
                    cache_path=DEDUP_CACHE_PATH,
                    retention_days=DEDUP_RETENTION_DAYS,
                )
                self.logger.info(f"去重已启用: cache={DEDUP_CACHE_PATH}, retention_days={DEDUP_RETENTION_DAYS}")
            except Exception as e:
                self.logger.warning(f"去重初始化失败，将继续但不做去重: {e}")
                self.deduper = None
        
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
            missing = []
            if not EMAIL_ENABLED:
                missing.append("EMAIL_ENABLED!=true")
            if not SENDER_EMAIL:
                missing.append("SENDER_EMAIL")
            if not SENDER_PASSWORD:
                missing.append("SENDER_PASSWORD")
            self.logger.info(f"邮件功能未启用（缺少/未开启: {', '.join(missing)}）")
        
        self.logger.info(f"Daily Summary Agent V3 初始化完成")
        self.logger.info(f"目标日期: {self.target_date_readable} ({self.days_ago}天前)")
        self.logger.info(f"论文保存: {self.papers_dir}")
        self.logger.info(f"总结保存: {self.output_dir}")
        self.logger.info(f"批量总结: 每 {V3_BATCH_SIZE} 篇调用一次LLM")
    
    def run(self):
        """运行Agent - 跨关键词汇总去重后分批总结（降低API调用次数）"""
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
            total_batches = 0
            all_articles = []
            
            # 1) 爬取：为每个关键词抓取论文（去重后汇总）
            for idx, keyword in enumerate(KEYWORDS, 1):
                keyword = keyword.strip()
                if not keyword:
                    continue
                
                self.logger.info("\n" + "=" * 80)
                self.logger.info(f"[{idx}/{len(KEYWORDS)}] 处理关键词: {keyword}")
                self.logger.info("=" * 80)
                
                try:
                    # 爬取该关键词在目标日期的论文
                    self.logger.info(f"\n[步骤 1/3] 爬取 [{keyword}] 在 {self.target_date_readable} 发布的论文...")
                    articles = self._crawl_keyword_papers(keyword)
                    
                    if not articles:
                        self.logger.warning(f"[{keyword}] 在 {self.target_date_readable} 未获取到论文")
                        continue
                    
                    self.logger.info(f"[{keyword}] 获取 {len(articles)} 篇论文")
                    total_articles += len(articles)
                    all_articles.extend(articles)
                    
                    self.logger.info(f"[{keyword}] 已加入汇总队列（当前累计 {len(all_articles)} 篇）")
                    
                except Exception as e:
                    self.logger.error(f"[{keyword}] 处理失败: {e}", exc_info=True)
                    continue

            # 2) 可选：抓取 Archive 并落盘（用于云盘同步与回溯）
            self._crawl_and_save_archive()

            # 3) 分批总结（每 N 篇调用一次LLM）
            all_articles = self._dedupe_in_memory(all_articles)
            if not all_articles:
                self.logger.warning("未获取到任何论文，结束任务")
                return

            all_articles.sort(key=lambda a: getattr(a, "publish_time", datetime.now()), reverse=True)
            batch_size = max(int(V3_BATCH_SIZE), 1)
            batches = [all_articles[i : i + batch_size] for i in range(0, len(all_articles), batch_size)]
            total_batches = len(batches)

            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"开始批量总结：共 {len(all_articles)} 篇论文，分 {total_batches} 批（每批≤{batch_size}）")
            self.logger.info("=" * 80)

            for batch_idx, batch_articles in enumerate(batches, 1):
                self.logger.info(f"\n[批次 {batch_idx}/{total_batches}] 生成批量小结...")
                batch_summary = self.summary_writer.generate_batch_summary(
                    articles=batch_articles,
                    batch_index=batch_idx,
                    total_batches=total_batches,
                    target_date=self.target_date_readable,
                )
                batch_file = self._save_batch_summary(batch_summary, batch_idx, total_batches)
                self.logger.info(f"[批次 {batch_idx}/{total_batches}] 已保存: {batch_file}")
            
            # 4. 生成汇总报告
            self.logger.info("\n" + "=" * 80)
            self.logger.info("任务完成！")
            self.logger.info("=" * 80)
            self.logger.info(f"目标日期: {self.target_date_readable}")
            self.logger.info(f"总关键词数: {len(KEYWORDS)}")
            self.logger.info(f"总论文数: {total_articles}")
            self.logger.info(f"生成批次数: {total_batches}")
            self.logger.info(f"论文保存目录: {self.papers_dir}")
            self.logger.info(f"总结保存目录: {self.output_dir}")
            self.logger.info("=" * 80)
            
            # 生成索引文件
            self._generate_index()
            
            # 5. 汇总所有批次小结
            if total_batches > 0:
                self.logger.info("\n" + "=" * 80)
                self.logger.info("汇总总结文档...")
                self.logger.info("=" * 80)
                
                aggregated_file = self._aggregate_and_send(total_batches)
                
                if aggregated_file:
                    self.logger.info(f"汇总文档: {aggregated_file}")
            
        except Exception as e:
            self.logger.error(f"执行任务时出错: {e}", exc_info=True)
            raise

    def _dedupe_in_memory(self, articles: list) -> list:
        """二次兜底去重：避免同一运行中出现重复key（例如手工拼接带来的重复）。"""
        if not articles:
            return []
        seen = set()
        kept = []
        for a in articles:
            if self.deduper is not None:
                key = self.deduper.make_key(a)
            else:
                key = getattr(a, "arxiv_id", None) or getattr(a, "url", None) or getattr(a, "title", None)
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(a)
        return kept

    def _save_batch_summary(self, summary: str, batch_idx: int, total_batches: int) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"batch_{batch_idx:02d}_of_{total_batches:02d}.md"
        path = self.output_dir / filename
        header = f"""---
title: 批量小结 {batch_idx}/{total_batches}
date: {self.target_date_str}
generated_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + summary)
        return path

    def _crawl_and_save_archive(self) -> None:
        """可选抓取 Archive 内容并保存到 data/archive/YYYYMMDD/ 便于云盘同步。"""
        try:
            if not ARCHIVE_URLS:
                return
            urls = [u.strip() for u in ARCHIVE_URLS if u and u.strip()]
            if not urls:
                return

            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"抓取 Archive 源：{len(urls)} 个URL")
            self.logger.info("=" * 80)

            articles = self.archive_crawler.crawl(urls=urls)
            if not articles:
                self.logger.warning("Archive 未抓取到文章")
                return

            archive_dir = Path(DATA_DIR) / "archive" / self.target_date_str
            archive_dir.mkdir(parents=True, exist_ok=True)
            json_path = archive_dir / "archive_articles.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)

            self.logger.info(f"Archive 已保存: {json_path}（{len(articles)} 篇）")
        except Exception as e:
            self.logger.error(f"Archive 抓取/保存失败: {e}", exc_info=True)
    
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

            # 去重：跨关键词/跨天避免重复分析同一篇论文
            if self.deduper is not None:
                deduped, stats = self.deduper.filter_new(
                    articles,
                    keyword=keyword,
                    date_str=self.target_date_str,
                )
                if stats.skipped > 0:
                    self.logger.info(f"[{keyword}] 去重跳过 {stats.skipped} 篇重复论文（保留 {stats.kept}）")
                return deduped

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
                f"\n## 批量小结列表（每 {V3_BATCH_SIZE} 篇一批）\n"
            ]

            batch_files = sorted(self.output_dir.glob("batch_*_of_*.md"))
            if batch_files:
                for bf in batch_files:
                    lines.append(f"- [{bf.name}](./{bf.name})")
            else:
                lines.append("- （未生成批量小结）")

            aggregated = self.output_dir / f"汇总总结_{self.target_date_str}.md"
            if aggregated.exists():
                lines.append(f"\n## 汇总文档\n")
                lines.append(f"- [汇总总结_{self.target_date_str}.md](./{aggregated.name})")
            
            lines.append(f"\n## 论文PDF")
            lines.append(f"\nPDF文件保存在: `{self.papers_dir.relative_to(Path.cwd())}/`")

            archive_json = Path(DATA_DIR) / "archive" / self.target_date_str / "archive_articles.json"
            if archive_json.exists():
                try:
                    rel = archive_json.relative_to(Path.cwd())
                except Exception:
                    rel = archive_json
                lines.append("\n## Archive 抓取结果")
                lines.append(f"\n- JSON: `{rel}`")
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            self.logger.info(f"索引文件已生成: {index_path}")
            
        except Exception as e:
            self.logger.error(f"生成索引文件失败: {e}")
    
    def _aggregate_and_send(self, total_summaries: int) -> Path:
        """汇总批量小结并发送邮件"""
        try:
            # 1. 生成汇总文档
            aggregated_file = self.output_dir / f"汇总总结_{self.target_date_str}.md"
            self.aggregator.aggregate_batch_summaries(
                summary_dir=self.output_dir,
                output_path=aggregated_file,
                date_str=self.target_date_str,
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
                subject = f"【AI论文每日总结】{date_readable} - {total_summaries}批"
                
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
