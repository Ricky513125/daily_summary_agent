"""总结汇总模块"""
from pathlib import Path
from typing import List
from datetime import datetime
from utils.logger import logger


class SummaryAggregator:
    """总结汇总器"""
    
    def __init__(self):
        self.logger = logger.bind(module="summary_aggregator")
    
    def aggregate_summaries(
        self,
        summary_dir: Path,
        output_path: Path,
        date_str: str,
        keywords: List[str]
    ) -> Path:
        """
        汇总多个关键词的总结为一个文档
        
        Args:
            summary_dir: 总结文件目录
            output_path: 输出文件路径
            date_str: 日期字符串（YYYYMMDD）
            keywords: 关键词列表
        
        Returns:
            Path: 汇总文件路径
        """
        try:
            self.logger.info(f"开始汇总总结文档: {summary_dir}")
            
            # 构建汇总文档
            lines = []
            
            # 添加标题和目录
            lines.extend(self._build_header(date_str, keywords))
            
            # 添加每个关键词的总结
            for idx, keyword in enumerate(keywords, 1):
                keyword = keyword.strip()
                if not keyword:
                    continue
                
                summary_file = self._get_summary_file(summary_dir, keyword)
                if not summary_file.exists():
                    self.logger.warning(f"总结文件不存在: {summary_file}")
                    continue
                
                # 读取并添加总结内容
                content = self._read_summary(summary_file, keyword, idx)
                lines.extend(content)
            
            # 添加统计信息
            lines.extend(self._build_footer(summary_dir, keywords))
            
            # 保存汇总文档
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            self.logger.info(f"汇总文档已生成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"汇总总结失败: {e}", exc_info=True)
            raise
    
    def _build_header(self, date_str: str, keywords: List[str]) -> List[str]:
        """构建文档头部"""
        date_readable = datetime.strptime(date_str, "%Y%m%d").strftime("%Y年%m月%d日")
        
        lines = [
            "---",
            f"title: {date_readable} AI论文每日总结",
            f"date: {date_str}",
            f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "---",
            "",
            f"# {date_readable} AI论文每日总结",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            "",
            "## 📋 目录",
            ""
        ]
        
        # 添加目录
        for idx, keyword in enumerate(keywords, 1):
            keyword = keyword.strip()
            if keyword:
                anchor = keyword.replace(" ", "-").replace("/", "-")
                lines.append(f"{idx}. [{keyword}](#{anchor})")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _get_summary_file(self, summary_dir: Path, keyword: str) -> Path:
        """获取总结文件路径"""
        safe_keyword = keyword.replace("/", "_").replace(" ", "_").replace("\\", "_")
        return summary_dir / f"summary_{safe_keyword}.md"
    
    def _read_summary(self, summary_file: Path, keyword: str, index: int) -> List[str]:
        """读取并格式化总结内容"""
        lines = [
            "",
            "---",
            "",
            f"## {index}. {keyword}",
            ""
        ]
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除YAML前置数据
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            
            # 移除第一个标题（通常是重复的关键词标题）
            content_lines = content.split('\n')
            if content_lines and content_lines[0].startswith('# '):
                content_lines = content_lines[1:]
            
            content = '\n'.join(content_lines).strip()
            lines.append(content)
            
        except Exception as e:
            self.logger.error(f"读取总结文件失败 {summary_file}: {e}")
            lines.append(f"*总结生成失败或文件不存在*")
        
        return lines
    
    def _build_footer(self, summary_dir: Path, keywords: List[str]) -> List[str]:
        """构建文档尾部"""
        lines = [
            "",
            "---",
            "",
            "## 📊 统计信息",
            ""
        ]
        
        # 统计文件
        summary_files = list(summary_dir.glob("summary_*.md"))
        total_summaries = len(summary_files)
        
        lines.append(f"- **关键词总数**: {len(keywords)}")
        lines.append(f"- **成功生成总结**: {total_summaries}")
        lines.append(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 统计论文数量
        papers_dir = summary_dir.parent.parent / "data" / "papers" / summary_dir.name
        if papers_dir.exists():
            total_papers = 0
            for keyword in keywords:
                keyword = keyword.strip()
                if not keyword:
                    continue
                safe_keyword = keyword.replace("/", "_").replace(" ", "_").replace("\\", "_")
                keyword_dir = papers_dir / safe_keyword
                if keyword_dir.exists():
                    pdf_files = list(keyword_dir.glob("*.pdf"))
                    total_papers += len(pdf_files)
            
            lines.append(f"- **论文PDF总数**: {total_papers}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*本文档由 Daily Summary Agent V3 自动生成*")
        lines.append("")
        
        return lines
