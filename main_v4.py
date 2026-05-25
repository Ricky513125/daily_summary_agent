"""主程序入口 V4 - 在 V3 基础上：
1) 扩展关键词（新增量化相关查询）
2) 剔除机器人硬件 / 医学 / 安全 等领域的论文
3) 使用 V4 写作器，提示词强化领域聚焦

设计原则：不修改 V1/V2/V3 任何代码，通过子类化 + 模块级 KEYWORDS 替换实现。
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import main_v3  # noqa: E402  保留原 V3 模块
from main_v3 import DailySummaryAgentV3  # noqa: E402
from config_v4 import KEYWORDS_V4, EXCLUDE_CATEGORIES_V4, EXCLUDE_KEYWORDS_V4  # noqa: E402
from writers.summary_writer_v4 import SummaryWriterV4  # noqa: E402
from utils.logger import logger  # noqa: E402


def _build_kw_pattern(keywords: list[str]) -> re.Pattern | None:
    """构造大小写不敏感的关键词匹配正则（子串匹配，已转义）。"""
    cleaned = [re.escape(k) for k in keywords if k]
    if not cleaned:
        return None
    return re.compile("|".join(cleaned), re.IGNORECASE)


class DailySummaryAgentV4(DailySummaryAgentV3):
    """V4 Agent：扩充关键词 + 领域排除过滤。"""

    def __init__(self, days_ago: int = None):
        # 在父类 run() 之前替换 main_v3 模块级 KEYWORDS（run() 内通过模块全局名查找）
        main_v3.KEYWORDS = list(KEYWORDS_V4)

        super().__init__(days_ago=days_ago)

        # 替换为 V4 写作器（更强的领域聚焦提示词）
        self.summary_writer = SummaryWriterV4()

        # 预编译排除规则
        self._exclude_categories = set(c.lower() for c in EXCLUDE_CATEGORIES_V4)
        self._exclude_kw_pattern = _build_kw_pattern(EXCLUDE_KEYWORDS_V4)

        self.logger = logger.bind(module="main_agent_v4")
        self.logger.info(
            f"V4 启用: 关键词 {len(KEYWORDS_V4)} 个；"
            f"排除分类 {len(self._exclude_categories)} 个；"
            f"排除关键词 {len(EXCLUDE_KEYWORDS_V4)} 个"
        )

    # ---------- 领域排除过滤 ----------
    def _categories_of(self, article) -> list[str]:
        """从 Article.content 中解析 arXiv 分类（_convert_to_article 把分类拼进了 content）。"""
        cats: list[str] = []
        content = getattr(article, "content", "") or ""
        m = re.search(r"## 分类\s*\n([^\n]+)", content)
        if m:
            cats = [c.strip() for c in m.group(1).split(",") if c.strip()]
        # 兼容：tags 中也可能含分类
        tags = getattr(article, "tags", None) or []
        cats.extend([t for t in tags if isinstance(t, str)])
        return cats

    def _should_exclude(self, article) -> tuple[bool, str]:
        # 1) 分类命中即排除
        for cat in self._categories_of(article):
            c = cat.lower()
            if c in self._exclude_categories:
                return True, f"category={cat}"
            # q-bio.* 前缀兜底
            if c.startswith("q-bio") and "q-bio" in self._exclude_categories:
                return True, f"category={cat}"

        # 2) 标题/摘要黑名单词命中即排除
        if self._exclude_kw_pattern is not None:
            text = f"{getattr(article, 'title', '')}\n{getattr(article, 'content', '')}"
            m = self._exclude_kw_pattern.search(text)
            if m:
                return True, f"keyword={m.group(0)!r}"

        return False, ""

    def _filter_excluded(self, articles: list, keyword: str) -> list:
        kept = []
        for a in articles:
            drop, reason = self._should_exclude(a)
            if drop:
                self.logger.info(f"[{keyword}] V4 排除: {a.title[:60]}... ({reason})")
                continue
            kept.append(a)
        if len(kept) != len(articles):
            self.logger.info(f"[{keyword}] V4 领域过滤: {len(articles)} -> {len(kept)}")
        return kept

    # 覆写：在 V3 抓取/去重后再做领域过滤
    def _crawl_keyword_papers(self, keyword: str) -> list:
        articles = super()._crawl_keyword_papers(keyword)
        return self._filter_excluded(articles, keyword)


def main():
    agent = DailySummaryAgentV4()
    agent.run()


if __name__ == "__main__":
    main()
