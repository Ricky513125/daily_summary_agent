"""主程序入口 V5 - 在 V4 基础上：
1. 移除 PDF 下载
2. 保留每篇论文的 LLM 短摘要（≤200字）
3. 移除批量小结和每日趋势汇总
4. 发邮件（含每篇短摘要）
"""
import json
import sys
import time
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
from config_v5 import KEYWORDS_V5, EXCLUDE_CATEGORIES_V5, EXCLUDE_KEYWORDS_V5  # noqa: E402
from writers.summary_writer_v4 import SummaryWriterV4  # noqa: E402
from utils.logger import logger  # noqa: E402
from utils.email_sender import EmailSender  # noqa: E402


class DailySummaryAgentV5(DailySummaryAgentV4):
    """V5 Agent：无 PDF 下载，逐篇 LLM 短摘要，无批量/每日汇总，发邮件。"""

    def __init__(self, days_ago: int = None):
        super().__init__(days_ago=days_ago)
        self.logger = logger.bind(module="main_agent_v5")
        self.summary_writer = SummaryWriterV4()
        # 覆盖 V4 的排除规则，使用 V5 专属配置
        from main_v4 import _build_kw_pattern
        self._exclude_categories = set(c.lower() for c in EXCLUDE_CATEGORIES_V5)
        self._exclude_kw_pattern = _build_kw_pattern(EXCLUDE_KEYWORDS_V5)
        self.logger.info("V5 启用: 无 PDF 下载 / 逐篇短摘要 / 无每日汇总")

    # ---------- 爬取（跳过 PDF 下载） ----------
    def _crawl_keyword_papers(self, keyword: str) -> list:
        start_time = self.target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        self.logger.info(
            f"[{keyword}] 查找时间范围: "
            f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}"
        )

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

        # 指数退避重试，应对 arXiv 429 限流
        for attempt in range(1, 4):
            try:
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

                return self._filter_excluded(articles, keyword)

            except Exception as e:
                is_429 = "429" in str(e)
                if is_429 and attempt < 3:
                    wait = 30 * (2 ** (attempt - 1))  # 30s, 60s
                    self.logger.warning(f"[{keyword}] 429 限流，{wait}s 后重试 (第{attempt}次)")
                    time.sleep(wait)
                else:
                    self.logger.error(f"[{keyword}] 爬取失败: {e}", exc_info=True)
                    return []

    # ---------- 告警邮件 ----------
    def _send_alert_email(self, subject: str, body: str) -> None:
        if not (self.email_enabled and RECEIVER_EMAILS):
            return
        html = (
            "<div style='font-family:Arial,sans-serif;border-left:4px solid #e74c3c;"
            "padding:12px 16px;background:#fff5f5;'>"
            f"<h3 style='color:#e74c3c;margin-top:0'>{subject}</h3>"
            f"<p>{body}</p>"
            f"<p style='color:#888;font-size:12px'>目标日期: {self.target_date_readable}</p>"
            "</div>"
        )
        try:
            self.email_sender.send_summary(
                receiver_emails=RECEIVER_EMAILS,
                subject=subject,
                content=html,
                attachments=[],
            )
            self.logger.info(f"告警邮件已发送: {subject}")
        except Exception as e:
            self.logger.error(f"告警邮件发送失败: {e}", exc_info=True)

    # ---------- 主流程：爬取 + 逐篇短摘要 + 发邮件 ----------
    def run(self):
        self.logger.info("=" * 80)
        self.logger.info(f"开始执行 V5 任务（目标日期: {self.target_date_readable}）")
        self.logger.info("=" * 80)

        try:
            self._run_inner()
        except Exception as e:
            self.logger.error(f"V5 任务异常终止: {e}", exc_info=True)
            import traceback
            tb = traceback.format_exc().replace("\n", "<br>").replace(" ", "&nbsp;")
            self._send_alert_email(
                subject=f"【告警】AI论文Agent执行失败 ({self.target_date_readable})",
                body=f"脚本执行过程中抛出异常，请检查 GitHub Actions 日志。<br><br>"
                     f"<pre style='background:#f8f8f8;padding:8px;font-size:11px'>{tb}</pre>",
            )
            raise

    def _run_inner(self):
        if not ENABLE_ARXIV:
            self.logger.warning("arXiv爬取未启用")
            return

        keywords = list(KEYWORDS_V5)
        if not keywords:
            self.logger.warning("未配置关键词")
            self._send_alert_email(
                subject=f"【告警】AI论文Agent未配置关键词 ({self.target_date_readable})",
                body="KEYWORDS_V4 为空，未执行任何检索。请检查 GitHub Actions 变量配置。",
            )
            return

        all_articles = []
        for idx, keyword in enumerate(keywords, 1):
            keyword = keyword.strip()
            if not keyword:
                continue
            self.logger.info(f"[{idx}/{len(keywords)}] 关键词: {keyword}")
            articles = self._crawl_keyword_papers(keyword)
            all_articles.extend(articles)
            if idx < len(keywords):
                time.sleep(4)  # arXiv 官方建议请求间隔 ≥3s

        # 内存去重 + 排序
        all_articles = self._dedupe_in_memory(all_articles)
        all_articles.sort(
            key=lambda a: getattr(a, "publish_time", datetime.now()), reverse=True
        )

        self.logger.info(f"共识别到 {len(all_articles)} 篇文献（去重后）")

        if not all_articles:
            self._send_alert_email(
                subject=f"【告警】AI论文Agent未检索到文献 ({self.target_date_readable})",
                body="所有关键词均未检索到符合条件的文献。可能原因：当天 arXiv 无新文章、"
                     "关键词过于严格、或网络/API 访问异常。",
            )
            return

        # 逐篇生成 ≤200字短摘要
        self.logger.info(f"开始逐篇生成短摘要：共 {len(all_articles)} 篇")
        paper_summaries_path = self.output_dir / "paper_summaries.jsonl"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(paper_summaries_path, "w", encoding="utf-8") as f:
            for idx, article in enumerate(all_articles, 1):
                self.logger.info(f"[{idx}/{len(all_articles)}] {article.title[:60]}...")
                short_summary = self.summary_writer.generate_paper_short_summary(
                    article=article,
                    target_date=self.target_date_readable,
                )
                article.short_summary = short_summary
                rec = {
                    "index": idx,
                    "title": getattr(article, "title", ""),
                    "url": getattr(article, "url", ""),
                    "arxiv_id": getattr(article, "arxiv_id", ""),
                    "publish_time": getattr(article, "publish_time", None).isoformat()
                    if getattr(article, "publish_time", None) else None,
                    "keywords": getattr(article, "tags", []),
                    "short_summary": short_summary,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.logger.info(f"短摘要已保存: {paper_summaries_path}")

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
                short_summary = (getattr(a, "short_summary", "") or "").replace("\n", "<br>")
                link = f'<a href="{url}">{arxiv_id or url}</a>' if url else arxiv_id
                rows.append(
                    f"<tr><td>{i}</td><td>{title}</td><td>{link}</td>"
                    f"<td>{kw}</td><td>{short_summary}</td></tr>"
                )

            body_lines = [
                f"<p><b>{date_readable}</b> 共识别到 <b>{len(articles)}</b> 篇符合条件的文献。</p>",
                "<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>",
                "<tr><th>#</th><th>标题</th><th>arXiv</th><th>匹配关键词</th><th>短摘要</th></tr>",
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
