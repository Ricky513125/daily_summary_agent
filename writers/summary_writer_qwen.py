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
        
        # 构建提示词（更强调可验证、低幻觉、可执行）
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        prompt_parts = [
            f"# 关键词: {keyword}",
            f"# 日期: {date_str}",
            f"\n共 {len(articles)} 篇相关论文。\n",
            "## 论文列表（仅材料，不要引入外部信息）\n"
        ]
        
        for idx, article in enumerate(articles, 1):
            prompt_parts.append(f"\n### P{idx}. {article.title}\n")
            prompt_parts.append(f"- 作者: {article.author}")
            prompt_parts.append(f"- 发布时间: {article.publish_time.strftime('%Y-%m-%d')}")
            prompt_parts.append(f"- 链接: {article.url}")
            # 控制长度，避免把上下文都浪费在长摘要上
            prompt_parts.append(f"- 摘要(截断): {article.content[:800]}\n")
        
        prompt_parts.append("\n---\n")
        prompt_parts.append("## 任务要求（非常重要）\n")
        prompt_parts.append("你将得到同一关键词下、同一天发布的多篇论文标题与摘要(截断)。请只基于这些材料写总结：")
        prompt_parts.append("1) 禁止编造：不要虚构未给出的实验结果、数据集、指标、数值、对比结论、SOTA宣称、代码开源信息等。")
        prompt_parts.append("2) 证据优先：每个关键判断/洞察后面用括号标注依据论文编号，例如（依据：P2,P5）。没有依据就写“材料未提供，无法判断”。")
        prompt_parts.append("3) 术语克制：摘要没出现的方法名/模块名不要强行补全；不确定就用更泛化表述。")
        prompt_parts.append("4) 可执行：建议必须可操作（下一步读什么/做什么/怎么验证），避免空话。")
        prompt_parts.append("\n请输出中文 Markdown，并严格按以下结构与标题（不要增删标题层级）：")
        prompt_parts.append("\n### 1) TL;DR（100-150字）")
        prompt_parts.append("- 3-5 个要点，句子短，尽量带（依据：Px）。")
        prompt_parts.append("\n### 2) 主题聚类（2-4类）")
        prompt_parts.append("- 每类：一句话概括 + 代表论文编号列表（如：P1,P3）+ 代表论文标题（可选）。")
        prompt_parts.append("\n### 3) 逐篇精读卡片（每篇 ≤4 行）")
        prompt_parts.append("对每篇论文按固定字段输出：")
        prompt_parts.append("- 一句话贡献：动词开头，描述作者做了什么")
        prompt_parts.append("- 方法要点：1-2点（仅来自材料）")
        prompt_parts.append("- 适用场景：可能解决什么问题/适合什么场景（不确定就写“材料未提供”）")
        prompt_parts.append("- 证据/限制：摘要里给了什么证据；若没有写“摘要未提供证据细节”")
        prompt_parts.append("\n### 4) 对比与洞察（3-6条）")
        prompt_parts.append("- 每条都要写出对比对象/维度，并在末尾给（依据：Px）。")
        prompt_parts.append("\n### 5) 可执行建议（3-5条）")
        prompt_parts.append("- 以“下一步”开头，包含验证动作与预期产出（例如：复现/补评测/读论文某章节）。")
        prompt_parts.append("\n### 6) 必读清单（3篇）")
        prompt_parts.append("- 每篇：为什么值得读（仅基于材料）+ 优先看什么（如：方法/实验/消融/局限章节）。")
        
        prompt = "\n".join(prompt_parts)
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个严谨的{keyword}领域研究分析与总结助手。\n"
                    "你必须遵守：\n"
                    "- 只使用用户提供的材料；不允许臆测、补全或“常识推断”成事实。\n"
                    "- 对所有洞察给出材料依据（用论文编号 Pn）；无法支持就明确写“材料未提供，无法判断”。\n"
                    "- 输出专业、凝练、可执行；避免空话、套话与过度泛化。\n"
                    "- 严格按用户给定的 Markdown 标题结构输出；不要添加额外小节。\n"
                )
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
                temperature=0.4,
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

    def generate_batch_summary(
        self,
        articles: List[Article],
        batch_index: int,
        total_batches: int,
        target_date: str = None,
    ) -> str:
        """对一批论文生成“小总结”（用于减少API调用次数）"""
        if not self.api_configured:
            self.logger.error("阿里千问API未配置，无法生成总结")
            date_str = target_date or datetime.now().strftime("%Y-%m-%d")
            return f"# 批次 {batch_index}/{total_batches}（{date_str}）\n\n*API未配置，略过生成。*\n"

        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        prompt_parts = [
            f"# 日期: {date_str}",
            f"# 批次: {batch_index}/{total_batches}",
            f"\n本批共 {len(articles)} 篇论文（跨多个关键词去重后汇总）。\n",
            "## 论文列表（仅材料，不要引入外部信息）\n",
        ]

        for idx, article in enumerate(articles, 1):
            prompt_parts.append(f"\n### P{idx}. {article.title}\n")
            if getattr(article, "author", None):
                prompt_parts.append(f"- 作者: {article.author}")
            if getattr(article, "publish_time", None):
                prompt_parts.append(f"- 发布时间: {article.publish_time.strftime('%Y-%m-%d')}")
            if getattr(article, "url", None):
                prompt_parts.append(f"- 链接: {article.url}")
            if getattr(article, "arxiv_id", None):
                prompt_parts.append(f"- arXiv ID: {getattr(article, 'arxiv_id')}")
            if getattr(article, "tags", None):
                prompt_parts.append(f"- 命中关键词: {', '.join(getattr(article, 'tags'))}")
            prompt_parts.append(f"- 摘要(截断): {article.content[:800]}\n")

        prompt_parts.append("\n---\n")
        prompt_parts.append("## 任务要求（非常重要）\n")
        prompt_parts.append("请只基于材料输出总结，禁止编造任何未给出的实验结果/数据/数值/对比结论。")
        prompt_parts.append("每条洞察都要在末尾标注依据论文编号，例如（依据：P2,P5）。")
        prompt_parts.append("如果材料不足以支持判断，请写“材料未提供，无法判断”。")
        prompt_parts.append("\n请输出中文 Markdown，并严格按以下结构（不要增删标题）：")
        prompt_parts.append("\n### 1) 本批TL;DR（6条以内）")
        prompt_parts.append("\n### 2) 主题线索（3-5条）")
        prompt_parts.append("- 每条：主题一句话 + 涉及论文编号（依据：Px）")
        prompt_parts.append("\n### 3) 值得跟进（最多5条）")
        prompt_parts.append("- 每条：为什么值得跟进 + 建议下一步怎么验证/复现（依据：Px）")
        prompt_parts.append("\n### 4) 论文速览（每篇1行）")
        prompt_parts.append("- 格式：P{n} | 一句话贡献（不超过20字）")

        prompt = "\n".join(prompt_parts)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个严谨的研究分析与总结助手。\n"
                    "- 只使用用户提供材料，不允许臆测。\n"
                    "- 所有洞察必须给出论文编号依据；无法支持就写“材料未提供，无法判断”。\n"
                    "- 输出专业、凝练、可执行，避免空话。\n"
                    "- 严格按用户给定标题结构输出。\n"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            self.logger.info(f"[batch {batch_index}/{total_batches}] 调用阿里千问API生成批量总结...")
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.4,
                max_tokens=3000,
            )
            if response.status_code == 200:
                summary = response.output.choices[0].message.content
                self.logger.info(f"[batch {batch_index}/{total_batches}] 批量总结生成成功")
                return summary
            error_msg = f"API调用失败: {response.message}"
            self.logger.error(f"[batch {batch_index}/{total_batches}] {error_msg}")
            return f"# 批次 {batch_index}/{total_batches}\n\n*生成失败：{error_msg}*\n"
        except Exception as e:
            self.logger.error(f"[batch {batch_index}/{total_batches}] 生成总结失败: {e}", exc_info=True)
            return f"# 批次 {batch_index}/{total_batches}\n\n*生成异常：{str(e)}*\n"
    
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
