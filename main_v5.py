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

    # ---------- 按分类抓取（替代逐关键词方式，大幅减少 API 调用次数） ----------
    def _crawl_by_category(self, category: str) -> list:
        """抓取目标日期该分类下的所有论文，返回 arxiv.Result 列表。"""
        date_from = self.target_date.strftime("%Y%m%d") + "0000"
        date_to = self.target_date.strftime("%Y%m%d") + "2359"
        query = f"cat:{category} AND submittedDate:[{date_from} TO {date_to}]"
        search = arxiv.Search(
            query=query,
            max_results=500,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        for attempt in range(1, 4):
            try:
                results = list(self.arxiv_crawler.client.results(search))
                self.logger.info(f"[{category}] 获取 {len(results)} 篇")
                return results
            except Exception as e:
                if "429" in str(e) and attempt < 3:
                    wait = 60 * (2 ** (attempt - 1))
                    self.logger.warning(f"[{category}] 429 限流，{wait}s 后重试 (第{attempt}次)")
                    time.sleep(wait)
                else:
                    self.logger.error(f"[{category}] 爬取失败: {e}", exc_info=True)
                    return []
        return []

    def _match_keywords(self, result) -> list:
        """返回该论文匹配到的所有 KEYWORDS_V5 关键词列表。"""
        text = (result.title + " " + result.summary).lower()
        return [kw for kw in KEYWORDS_V5 if kw.lower() in text]

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

        categories = ARXIV_CATEGORIES or ["cs.CL", "cs.CV", "cs.AI", "cs.LG"]
        self.logger.info(f"按分类抓取（{len(categories)} 个分类，替代逐关键词方式）")

        # Step 1: 按分类抓取（4 次请求，取代 40 次）
        seen_ids: set = set()
        raw_results = []
        for idx, cat in enumerate(categories, 1):
            self.logger.info(f"[{idx}/{len(categories)}] 分类: {cat}，目标日期: {self.target_date_readable}")
            results = self._crawl_by_category(cat)
            for r in results:
                if r.entry_id not in seen_ids:
                    seen_ids.add(r.entry_id)
                    raw_results.append(r)
            if idx < len(categories):
                time.sleep(10)  # 分类间短暂等待

        self.logger.info(f"分类抓取完成，共 {len(raw_results)} 篇（跨分类去重后）")

        # Step 2: Python 侧关键词匹配 + 排除过滤
        all_articles = []
        for result in raw_results:
            matched_kws = self._match_keywords(result)
            if not matched_kws:
                continue
            article = self.arxiv_crawler._convert_to_article(result, matched_kws[0])
            if not article:
                continue
            article.tags = matched_kws
            filtered = self._filter_excluded([article], matched_kws[0])
            if filtered:
                all_articles.append(filtered[0])

        self.logger.info(f"关键词匹配 + 排除过滤后：{len(all_articles)} 篇")

        # Step 3: 持久化去重（跨天）
        if self.deduper is not None:
            all_articles, stats = self.deduper.filter_new(
                all_articles, date_str=self.target_date_str
            )
            if stats.skipped > 0:
                self.logger.info(f"持久化去重跳过 {stats.skipped} 篇（保留 {stats.kept}）")

        # Step 4: 内存去重 + 排序
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
