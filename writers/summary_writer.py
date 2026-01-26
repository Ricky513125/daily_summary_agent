"""总结撰写器"""
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import dashscope
from config import DASHSCOPE_API_KEY, QWEN_MODEL, OUTPUT_DIR
from utils.logger import logger
from crawlers.base_crawler import Article
import json


class SummaryWriter:
    """总结撰写器"""
    
    def __init__(self):
        self.logger = logger.bind(module="summary_writer")
        if DASHSCOPE_API_KEY:
            dashscope.api_key = DASHSCOPE_API_KEY
            self.api_configured = True
        else:
            self.api_configured = False
            self.logger.warning("DashScope API密钥未配置")
    
    def generate_summary(
        self,
        articles: List[Article],
        categories: Optional[Dict[str, List[Article]]] = None,
        stats: Optional[Dict] = None
    ) -> str:
        """生成总结"""
        if not self.api_configured:
            self.logger.error("DashScope API未配置，无法生成总结")
            return "DashScope API未配置"
        
        # 准备提示词
        prompt = self._build_prompt(articles, categories, stats)
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的AI、大模型、计算机视觉领域的内容总结专家。请根据提供的文章内容，生成一份结构清晰、内容丰富的每日总结报告。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = dashscope.ChatCompletion.call(
                model=QWEN_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4000,
                result_format='message'  # 返回格式为message
            )
            
            if response.status_code == 200:
                summary = response.output.choices[0].message.content
                self.logger.info("总结生成成功")
                return summary
            else:
                error_msg = f"API调用失败: {response.message}"
                self.logger.error(error_msg)
                return f"生成总结时出错: {error_msg}"
        except Exception as e:
            self.logger.error(f"生成总结失败: {e}", exc_info=True)
            return f"生成总结时出错: {str(e)}"
    
    def _build_prompt(self, articles: List[Article], categories: Optional[Dict[str, List[Article]]] = None, stats: Optional[Dict] = None) -> str:
        """构建提示词"""
        prompt_parts = []
        
        # 添加统计信息
        if stats:
            prompt_parts.append(f"## 统计信息\n")
            prompt_parts.append(f"- 总文章数: {stats.get('total', 0)}")
            prompt_parts.append(f"- 去重后: {stats.get('unique', 0)}")
            prompt_parts.append(f"- 今日文章: {stats.get('today', 0)}")
            if stats.get('by_category'):
                prompt_parts.append(f"- 分类统计: {json.dumps(stats['by_category'], ensure_ascii=False)}")
            prompt_parts.append("")
        
        # 添加分类信息
        if categories:
            prompt_parts.append("## 文章分类\n")
            for category, articles_list in categories.items():
                prompt_parts.append(f"\n### {category} ({len(articles_list)}篇)\n")
                for article in articles_list[:5]:  # 每个类别最多5篇
                    prompt_parts.append(f"- **{article.title}**")
                    prompt_parts.append(f"  - 来源: {article.source}")
                    prompt_parts.append(f"  - 链接: {article.url}")
                    prompt_parts.append(f"  - 摘要: {article.content[:300]}...")
                    prompt_parts.append("")
        else:
            # 如果没有分类，直接列出文章
            prompt_parts.append("## 文章列表\n")
            for article in articles[:20]:  # 最多20篇
                prompt_parts.append(f"- **{article.title}**")
                prompt_parts.append(f"  - 来源: {article.source}")
                prompt_parts.append(f"  - 链接: {article.url}")
                prompt_parts.append(f"  - 摘要: {article.content[:300]}...")
                prompt_parts.append("")
        
        prompt_parts.append("\n## 任务要求\n")
        prompt_parts.append("请根据以上文章内容，生成一份今日AI、大模型、计算机视觉领域的内容总结报告。")
        prompt_parts.append("报告应包括：")
        prompt_parts.append("1. 今日概览（总体情况）")
        prompt_parts.append("2. 重要新闻和动态")
        prompt_parts.append("3. 技术进展和突破")
        prompt_parts.append("4. 行业趋势和观点")
        prompt_parts.append("5. 总结和展望")
        prompt_parts.append("\n请使用Markdown格式，确保内容结构清晰、重点突出。")
        
        return "\n".join(prompt_parts)
    
    def save_summary(self, summary: str, filename: str = None) -> Path:
        """保存总结到文件"""
        if filename is None:
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"daily_summary_{date_str}.md"
        
        filepath = OUTPUT_DIR / filename
        
        # 添加元数据
        header = f"""---
title: 每日AI总结报告
date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
        
        content = header + summary
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"总结已保存到: {filepath}")
        return filepath
    
    def write_with_rag(
        self,
        retriever,
        query: str = "今日AI、大模型、计算机视觉领域的重要内容和趋势",
        top_k: int = 10
    ) -> str:
        """使用RAG生成总结"""
        if not self.api_configured:
            return "DashScope API未配置"
        
        # 检索相关内容
        results = retriever.retrieve(query, top_k=top_k)
        
        # 格式化检索结果
        context = retriever.format_results(results)
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的AI、大模型、计算机视觉领域的内容总结专家。请根据检索到的相关内容，生成一份结构清晰、内容丰富的每日总结报告。"
            },
            {
                "role": "user",
                "content": f"请根据以下检索到的内容，生成今日AI、大模型、计算机视觉领域的总结报告：\n\n{context}\n\n请生成一份结构清晰、内容丰富的Markdown格式报告。"
            }
        ]
        
        try:
            response = dashscope.ChatCompletion.call(
                model=QWEN_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4000,
                result_format='message'
            )
            
            if response.status_code == 200:
                summary = response.output.choices[0].message.content
                self.logger.info("RAG总结生成成功")
                return summary
            else:
                error_msg = f"API调用失败: {response.message}"
                self.logger.error(error_msg)
                return f"生成总结时出错: {error_msg}"
        except Exception as e:
            self.logger.error(f"RAG总结生成失败: {e}", exc_info=True)
            return f"生成总结时出错: {str(e)}"
