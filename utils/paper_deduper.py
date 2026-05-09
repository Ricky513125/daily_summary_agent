"""论文去重缓存（跨天持久化）"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_key(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return f"sha1:{digest}"


@dataclass
class DedupStats:
    kept: int = 0
    skipped: int = 0


class PersistentPaperDeduper:
    """
    基于本地 JSON 文件的论文去重器。

    - 主要 key 使用 arXiv ID（若存在），否则回退到 URL 或标题哈希。
    - 默认“全局去重”：一旦处理过，就在 retention 周期内跳过。
    """

    def __init__(self, cache_path: str | Path, retention_days: int = 180):
        self.cache_path = Path(cache_path)
        self.retention_days = max(int(retention_days), 1)
        self._seen_in_run: set[str] = set()
        self._data = self._load()
        self._gc()

    def _load(self) -> dict:
        try:
            if self.cache_path.exists():
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "papers" in data and isinstance(data["papers"], dict):
                    return data
        except Exception:
            pass

        return {"version": 1, "updated_at": None, "papers": {}}

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data["updated_at"] = _utc_now().isoformat()
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, sort_keys=True)

    def _gc(self) -> None:
        papers: dict = self._data.get("papers", {})
        if not isinstance(papers, dict) or not papers:
            return

        cutoff = _utc_now() - timedelta(days=self.retention_days)
        to_delete: list[str] = []
        for key, meta in papers.items():
            if not isinstance(meta, dict):
                to_delete.append(key)
                continue
            last_seen = meta.get("last_seen_utc")
            if not isinstance(last_seen, str):
                continue
            try:
                ts = datetime.fromisoformat(last_seen)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    to_delete.append(key)
            except Exception:
                continue

        for key in to_delete:
            papers.pop(key, None)

        self._data["papers"] = papers

    def make_key(self, article) -> str:
        arxiv_id = getattr(article, "arxiv_id", None)
        if isinstance(arxiv_id, str) and arxiv_id.strip():
            return f"arxiv:{arxiv_id.strip()}"

        url = getattr(article, "url", None)
        if isinstance(url, str) and url.strip():
            return _safe_key(url.strip())

        title = getattr(article, "title", None)
        if isinstance(title, str) and title.strip():
            return _safe_key(title.strip())

        return _safe_key(repr(article))

    def filter_new(
        self,
        articles: Iterable,
        *,
        keyword: Optional[str] = None,
        date_str: Optional[str] = None,
        persist: bool = True,
    ) -> tuple[list, DedupStats]:
        papers: dict = self._data.setdefault("papers", {})
        kept: list = []
        stats = DedupStats()

        for article in articles:
            key = self.make_key(article)
            if key in self._seen_in_run or key in papers:
                stats.skipped += 1
                # 记录额外命中的 keyword/date，便于追溯
                meta = papers.get(key)
                if isinstance(meta, dict):
                    meta["last_seen_utc"] = _utc_now().isoformat()
                    if keyword:
                        kws = meta.get("keywords")
                        if not isinstance(kws, list):
                            kws = []
                        if keyword not in kws:
                            kws.append(keyword)
                        meta["keywords"] = kws
                    if date_str:
                        dates = meta.get("dates")
                        if not isinstance(dates, list):
                            dates = []
                        if date_str not in dates:
                            dates.append(date_str)
                        meta["dates"] = dates
                    papers[key] = meta
                continue

            kept.append(article)
            stats.kept += 1
            self._seen_in_run.add(key)

            title = getattr(article, "title", None)
            meta = {
                "title": title if isinstance(title, str) else None,
                "first_seen_utc": _utc_now().isoformat(),
                "last_seen_utc": _utc_now().isoformat(),
                "keywords": [keyword] if keyword else [],
                "dates": [date_str] if date_str else [],
            }
            papers[key] = meta

        self._data["papers"] = papers
        if persist and (stats.kept > 0 or stats.skipped > 0):
            self._save()

        return kept, stats
