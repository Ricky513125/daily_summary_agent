"""主程序入口 V5 - 在 V4 基础上：
1. 移除 PDF 下载
2. 移除 LLM 总结
3. 只统计文献数，发一封简短邮件（标题 + arXiv 链接列表）
"""
import sys
import arxiv
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import main_v3  # noqa: E402
from main_v4 import DailySummaryAgentV4  # noqa: E402
from config import (  # noqa: E402
    ARXIV_CATEGORIES, ARXIV_MAX_RESULTS_PER_KEYWORD,
    ENABLE_ARXIV,
    EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT,
    SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAILS,
)
from config_v4 import KEYWORDS_V4  # noqa: E402
from utils.logger import logger  # noqa: E402
from utils.email_sender import EmailSender  # noqa: E402


class DailySummaryAgentV5(DailySummaryAgentV4):
    """V5 Agent：无 PDF 下载、无 LLM，仅统计文献数并发邮件。"""

    def __init__(self, days_ago: int = None):
        super().__init__(days_ago=days_ago)
        self.logger = logger.bind(module="main_agent_v5")
        self.logger.info("V5 启用: 无 PDF 下载 / 无 LLM 总结")

    # ---------- 爬取（跳过 PDF 下载） ----------
    def _crawl_keyword_papers(self, keyword: str) -> list:
        start_time = self.target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        self.logger.info(
            f"[{keyword}] 查找时间范围: "
            f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}"
        )

        try:
            search_query = f'(ti:"{keyword}" OR abs:"{keyword}")'
            if ARXIV_CATEGORIES:
                cat_queries = [f"cat:{cat}" for cat in ARXIV_CATEGORIES]
                search_query += f" AND ({' OR '.join(cat_queries)})"

            search = arxiv.Search(
                query=search_query,
                max_results=ARXIV_MAX_RESULTS_PER_KEYWORD * 5,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            articles = []
            for result in self.arxiv_crawler.client.results(search):
                if start_time <= result.published < end_time:
                    article = self.arxiv_crawler._convert_to_article(result, keyword)
                    if article:
                        articles.append(article)
                        self.logger.info(f"[{keyword}] 找到: {article.title[:60]}...")
                        if len(articles) >= ARXIV_MAX_RESULTS_PER_KEYWORD:
                            break

                if result.published < start_time - timedelta(days=2):
                    break

            # 去重
            if self.deduper is not None:
                deduped, stats = self.deduper.filter_new(
                    articles, keyword=keyword, date_str=self.target_date_str
                )
                if stats.skipped > 0:
                    self.logger.info(
                        f"[{keyword}] 去重跳过 {stats.skipped} 篇（保留 {stats.kept}）"
                    )
                articles = deduped

            # V4 领域排除过滤
            return self._filter_excluded(articles, keyword)

        except Exception as e:
            self.logger.error(f"[{keyword}] 爬取失败: {e}", exc_info=True)
            return []

    # ---------- 主流程：只爬取 + 发邮件 ----------
    def run(self):
        self.logger.info("=" * 80)
        self.logger.info(f"开始执行 V5 任务（仅统计，目标日期: {self.target_date_readable}）")
        self.logger.info("=" * 80)

        if not ENABLE_ARXIV:
            self.logger.warning("arXiv爬取未启用")
            return

        keywords = list(main_v3.KEYWORDS)
        if not keywords:
            self.logger.warning("未配置关键词")
            return

        all_articles = []
        for idx, keyword in enumerate(keywords, 1):
            keyword = keyword.strip()
            if not keyword:
                continue
            self.logger.info(f"[{idx}/{len(keywords)}] 关键词: {keyword}")
            articles = self._crawl_keyword_papers(keyword)
            all_articles.extend(articles)

        # 内存去重
        all_articles = self._dedupe_in_memory(all_articles)
        all_articles.sort(
            key=lambda a: getattr(a, "publish_time", datetime.now()), reverse=True
        )

        self.logger.info(f"共识别到 {len(all_articles)} 篇文献（去重后）")

        self._send_summary_email(all_articles)

    # ---------- 发简短统计邮件 ----------
    def _send_summary_email(self, articles: list) -> None:
        if not (self.email_enabled and RECEIVER_EMAILS):
            self.logger.info("邮件功能未启用或未配置收件人，跳过发送")
            return

        date_readable = datetime.strptime(self.target_date_str, "%Y%m%d").strftime("%Y年%m月%d日")
        subject = f"【AI论文每日统计】{date_readable} - 共 {len(articles)} 篇"

        if not articles:
            body_lines = [
                f"<p>{date_readable} 未检索到符合条件的文献。</p>",
                "<p>建议检查关键词或分类配置。</p>",
            ]
        else:
            rows = []
            for i, a in enumerate(articles, 1):
                title = (getattr(a, "title", "") or "").replace("\n", " ").strip()
                url = getattr(a, "url", "") or ""
                arxiv_id = getattr(a, "arxiv_id", "") or ""
                kw = ", ".join(getattr(a, "tags", []) or [])
                link = f'<a href="{url}">{arxiv_id or url}</a>' if url else arxiv_id
                rows.append(
                    f"<tr><td>{i}</td><td>{title}</td><td>{link}</td><td>{kw}</td></tr>"
                )

            body_lines = [
                f"<p><b>{date_readable}</b> 共识别到 <b>{len(articles)}</b> 篇符合条件的文献。</p>",
                "<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>",
                "<tr><th>#</th><th>标题</th><th>arXiv</th><th>匹配关键词</th></tr>",
                *rows,
                "</table>",
            ]

        html = "\n".join(body_lines)

        try:
            self.email_sender.send_summary(
                receiver_emails=RECEIVER_EMAILS,
                subject=subject,
                content=html,
                attachments=[],
            )
            self.logger.info(f"邮件已发送: {RECEIVER_EMAILS}")
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}", exc_info=True)


def main():
    agent = DailySummaryAgentV5()
    agent.run()


if __name__ == "__main__":
    main()
