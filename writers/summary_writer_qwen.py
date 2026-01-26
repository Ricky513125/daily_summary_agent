"""总结撰写器 - 使用阿里千问"""
from typing import List
from datetime import datetime
from pathlib import Path
import dashscope
from dashscope import Generation
from config import DASHSCOPE_API_KEY, QWEN_MODEL, OUTPUT_DIR
from utils.logger import logger
from crawlers.base_crawler import Article


class SummaryWriterQwen:
    """总结撰写器 - 使用阿里千问"""
    
    def __init__(self):
        self.logger = logger.bind(module="summary_writer_qwen")
        if DASHSCOPE_API_KEY:
            dashscope.api_key = DASHSCOPE_API_KEY
            self.api_configured = True
            self.logger.info("阿里千问API已配置")
        else:
            self.api_configured = False
            self.logger.warning("阿里千问API密钥未配置")
    
    def generate_keyword_summary(self, keyword: str, articles: List[Article], target_date: str = None) -> str:
        """为单个关键词生成总结
        
        Args:
            keyword: 关键词
            articles: 文章列表
            target_date: 目标日期（如 2026-01-24）
        """
        if not self.api_configured:
            self.logger.error("阿里千问API未配置，无法生成总结")
            return self._generate_simple_summary(keyword, articles, target_date)
        
        # 构建提示词
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        prompt_parts = [
            f"# 关键词: {keyword}",
            f"# 日期: {date_str}",
            f"\n共 {len(articles)} 篇相关论文\n",
            "## 论文列表\n"
        ]
        
        for idx, article in enumerate(articles, 1):
            prompt_parts.append(f"\n### 论文 {idx}: {article.title}\n")
            prompt_parts.append(f"**作者**: {article.author}")
            prompt_parts.append(f"**发布时间**: {article.publish_time.strftime('%Y-%m-%d')}")
            prompt_parts.append(f"**链接**: {article.url}")
            prompt_parts.append(f"\n**摘要**:\n{article.content[:1000]}\n")
        
        prompt_parts.append("\n---\n")
        prompt_parts.append(f"\n## 任务要求\n")
        prompt_parts.append(f"请针对关键词「{keyword}」，根据 {date_str} 发布的以上论文内容，生成一份详细的中文总结报告。")
        prompt_parts.append("\n报告应包括：")
        prompt_parts.append(f"1. {keyword}领域概览")
        prompt_parts.append("2. 主要研究方向和热点")
        prompt_parts.append("3. 重要论文亮点（逐一介绍，包含论文标题、作者、核心创新点）")
        prompt_parts.append("4. 技术趋势和发展方向")
        prompt_parts.append("5. 总结和展望")
        prompt_parts.append("\n请使用中文Markdown格式，确保内容结构清晰、重点突出、专业准确。")
        
        prompt = "\n".join(prompt_parts)
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": f"你是一个专业的{keyword}领域研究总结专家。请根据提供的论文内容，生成一份结构清晰、内容丰富、专业准确的中文总结报告。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            self.logger.info(f"[{keyword}] 调用阿里千问API生成总结...")
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format='message',
                temperature=0.7,
                max_tokens=4000
            )
            
            if response.status_code == 200:
                summary = response.output.choices[0].message.content
                self.logger.info(f"[{keyword}] 总结生成成功")
                return summary
            else:
                error_msg = f"API调用失败: {response.message}"
                self.logger.error(f"[{keyword}] {error_msg}")
                return self._generate_simple_summary(keyword, articles, target_date)
                
        except Exception as e:
            self.logger.error(f"[{keyword}] 生成总结失败: {e}", exc_info=True)
            return self._generate_simple_summary(keyword, articles, target_date)
    
    def _generate_simple_summary(self, keyword: str, articles: List[Article], target_date: str = None) -> str:
        """生成简单的论文列表（当API失败时）"""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# {keyword} - 论文列表",
            f"\n日期: {date_str}",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n共 {len(articles)} 篇论文\n",
            "---\n"
        ]
        
        for idx, article in enumerate(articles, 1):
            lines.append(f"\n## {idx}. {article.title}\n")
            lines.append(f"**作者**: {article.author}\n")
            lines.append(f"**发布时间**: {article.publish_time.strftime('%Y-%m-%d')}\n")
            lines.append(f"**arXiv ID**: {getattr(article, 'arxiv_id', 'N/A')}\n")
            lines.append(f"**链接**: {article.url}\n")
            if hasattr(article, 'pdf_path') and article.pdf_path:
                lines.append(f"**PDF**: {article.pdf_path}\n")
            lines.append(f"\n**摘要**:\n{article.content}\n")
            lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def save_summary(self, summary: str, keyword: str, date_str: str) -> Path:
        """保存总结到文件
        
        Args:
            summary: 总结内容
            keyword: 关键词
            date_str: 日期字符串（YYYYMMDD格式）
        
        Returns:
            Path: 保存的文件路径
        """
        # 创建日期目录
        date_dir = OUTPUT_DIR / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（清理特殊字符）
        safe_keyword = keyword.replace("/", "_").replace(" ", "_").replace("\\", "_")
        filename = f"summary_{safe_keyword}.md"
        filepath = date_dir / filename
        
        # 添加元数据
        header = f"""---
title: {keyword} 论文总结
date: {date_str}
keyword: {keyword}
generated_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
        
        content = header + summary
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"[{keyword}] 总结已保存到: {filepath}")
        return filepath
