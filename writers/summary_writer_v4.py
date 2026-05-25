"""V4 总结撰写器：在 V3 千问版基础上，强化提示词的领域聚焦与排除约束。

关注：大模型 / 多模态 / 视觉语言 / 训练与后训练 / 强化学习对齐 / 量化与推理加速
排除：机器人硬件本体、医学/生物医学、网络与系统安全/密码
"""
from typing import List
from datetime import datetime

from writers.summary_writer_qwen import SummaryWriterQwen
from crawlers.base_crawler import Article
from config import QWEN_MODEL

import dashscope
from dashscope import Generation


_FOCUS_BLOCK = (
    "【关注领域（白名单，仅当材料与之相关时才详细分析）】\n"
    "- 大语言模型 / 多模态大模型 / 视觉语言模型 / 扩散模型 / Transformer 架构\n"
    "- 训练与后训练：SFT、指令微调、RLHF、DPO、偏好优化、推理增强（CoT 等）\n"
    "- 模型量化与低比特推理：PTQ、QAT、INT4/INT8/FP8、GPTQ/AWQ/SmoothQuant、KV cache 量化、混合精度\n"
    "- LLM 推理加速与部署：speculative decoding、PagedAttention、FlashAttention、Serving 优化\n"
    "\n"
    "【排除领域（若材料明显属于以下任一类，请在该篇精读卡片标注“[超出关注范围]”并仅用1行带过）】\n"
    "- 机器人硬件/本体相关：机械臂、抓取、灵巧手、人形机器人、足式运动、自动驾驶、无人机、SLAM 等\n"
    "- 医学/生物医学：临床、影像（MRI/CT/X 光/超声/病理）、EHR、基因组、药物发现、疾病诊断等\n"
    "- 网络与系统安全/密码学：恶意软件、入侵检测、漏洞利用、侧信道、后门/木马、密码协议等\n"
)


class SummaryWriterV4(SummaryWriterQwen):
    """V4 写作器：复用 V3 的 API 调用与保存逻辑，仅重写 system prompt 的领域聚焦。"""

    def generate_keyword_summary(self, keyword: str, articles: List[Article], target_date: str = None) -> str:
        if not self.api_configured:
            self.logger.error("阿里千问API未配置，无法生成总结")
            return self._generate_simple_summary(keyword, articles, target_date)

        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        prompt_parts = [
            f"# 关键词: {keyword}",
            f"# 日期: {date_str}",
            f"\n共 {len(articles)} 篇相关论文。\n",
            "## 论文列表（仅材料，不要引入外部信息）\n",
        ]
        for idx, article in enumerate(articles, 1):
            prompt_parts.append(f"\n### P{idx}. {article.title}\n")
            prompt_parts.append(f"- 作者: {article.author}")
            prompt_parts.append(f"- 发布时间: {article.publish_time.strftime('%Y-%m-%d')}")
            prompt_parts.append(f"- 链接: {article.url}")
            prompt_parts.append(f"- 摘要(截断): {article.content[:800]}\n")

        prompt_parts.append("\n---\n")
        prompt_parts.append("## 任务要求（非常重要）\n")
        prompt_parts.append("你将得到同一关键词下、同一天发布的多篇论文标题与摘要(截断)。请只基于这些材料写总结：")
        prompt_parts.append("1) 禁止编造：不要虚构未给出的实验结果、数据集、指标、数值、对比结论、SOTA宣称、代码开源信息等。")
        prompt_parts.append("2) 证据优先：每个关键判断/洞察后面用括号标注依据论文编号，例如（依据：P2,P5）。没有依据就写“材料未提供，无法判断”。")
        prompt_parts.append("3) 术语克制：摘要没出现的方法名/模块名不要强行补全；不确定就用更泛化表述。")
        prompt_parts.append("4) 可执行：建议必须可操作（下一步读什么/做什么/怎么验证），避免空话。")
        prompt_parts.append("5) 领域聚焦：优先详细分析“关注领域”范围内的论文；属于“排除领域”的论文，每篇仅用 1 行带过并标注“[超出关注范围]”。")
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
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个严谨的{keyword}领域研究分析与总结助手，重点关注大模型/多模态/视觉/训练/量化/推理加速。\n"
                    "你必须遵守：\n"
                    "- 只使用用户提供的材料；不允许臆测、补全或“常识推断”成事实。\n"
                    "- 对所有洞察给出材料依据（用论文编号 Pn）；无法支持就明确写“材料未提供，无法判断”。\n"
                    "- 输出专业、凝练、可执行；避免空话、套话与过度泛化。\n"
                    "- 严格按用户给定的 Markdown 标题结构输出；不要添加额外小节。\n\n"
                    + _FOCUS_BLOCK
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            self.logger.info(f"[{keyword}] 调用阿里千问API生成总结 (V4)...")
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.4,
                max_tokens=4000,
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            self.logger.error(f"[{keyword}] API调用失败: {response.message}")
            return self._generate_simple_summary(keyword, articles, target_date)
        except Exception as e:
            self.logger.error(f"[{keyword}] 生成总结失败: {e}", exc_info=True)
            return self._generate_simple_summary(keyword, articles, target_date)

    def generate_paper_short_summary(self, article: Article, target_date: str = None) -> str:
        if not self.api_configured:
            self.logger.error("阿里千问API未配置，无法生成摘要")
            return ""

        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        title = getattr(article, "title", "")
        url = getattr(article, "url", "")
        authors = getattr(article, "author", "")
        arxiv_id = getattr(article, "arxiv_id", "")
        abstract = (getattr(article, "content", "") or "")[:1200]

        prompt = "\n".join([
            f"# 日期: {date_str}",
            "# 任务: 单篇论文极简摘要 (V4，关注大模型/视觉/量化)",
            "",
            "## 材料",
            f"- 标题: {title}",
            f"- 作者: {authors}",
            f"- arXiv ID: {arxiv_id}",
            f"- 链接: {url}",
            f"- 摘要(截断): {abstract}",
            "",
            "## 输出要求（必须严格遵守）",
            "1) 只基于材料，不要编造任何未给出的实验结果/数值/对比结论。",
            "2) 输出为中文纯文本（不要Markdown，不要列表符号）。",
            "3) 总长度≤200个中文字符（超出会被判失败）。",
            "4) 结构建议：一句话写“做了什么/怎么做/解决什么”。信息不足就写“材料未提供，无法判断”。",
            "5) 若材料明显属于机器人硬件/医学/网络安全等排除领域，请在末尾追加“[超出关注范围]”。",
        ])

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个严谨的论文摘要助手（V4），重点聚焦大模型/多模态/视觉/训练/量化/推理加速。\n"
                    "只使用用户提供材料，不允许臆测；输出必须≤200个中文字符且为纯文本。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.3,
                max_tokens=600,
            )
            if response.status_code != 200:
                self.logger.error(f"单篇摘要API调用失败: {response.message}")
                return ""
            text = (response.output.choices[0].message.content or "").strip()
            text = " ".join(text.split())
            return text[:200]
        except Exception as e:
            self.logger.error(f"单篇摘要生成失败: {e}", exc_info=True)
            return ""

    def generate_batch_summary(
        self,
        articles: List[Article],
        batch_index: int,
        total_batches: int,
        target_date: str = None,
    ) -> str:
        if not self.api_configured:
            date_str = target_date or datetime.now().strftime("%Y-%m-%d")
            return f"# 批次 {batch_index}/{total_batches}（{date_str}）\n\n*API未配置，略过生成。*\n"

        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        prompt_parts = [
            f"# 日期: {date_str}",
            f"# 批次: {batch_index}/{total_batches}",
            f"\n本批共 {len(articles)} 篇论文（跨多个关键词去重后汇总）。\n",
            "## 论文短摘要列表（仅材料，不要引入外部信息）\n",
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
            short_summary = getattr(article, "short_summary", "") or ""
            prompt_parts.append(f"- 短摘要(≤200字): {short_summary}\n")

        prompt_parts.append("\n---\n")
        prompt_parts.append("## 任务要求（非常重要）\n")
        prompt_parts.append("你只能使用上面每篇论文的“短摘要(≤200字)”作为信息来源，不要使用外部知识或你自己的背景常识来补全事实。")
        prompt_parts.append("禁止编造任何未给出的实验结果/数据/数值/对比结论/开源信息。")
        prompt_parts.append("每条洞察都要在末尾标注依据论文编号，例如（依据：P2,P5）。")
        prompt_parts.append("如果短摘要不足以支持判断，请写“材料未提供，无法判断”。")
        prompt_parts.append("领域聚焦：优先归纳关注领域（LLM/多模态/视觉/训练/量化/推理加速）的趋势；属于排除领域（机器人硬件/医学/安全）的论文可忽略或合并为一行说明。")
        prompt_parts.append("\n请输出中文 Markdown，并严格按以下结构（不要增删标题）：")
        prompt_parts.append("\n### 1) 本批研究趋势（3-6条）")
        prompt_parts.append("\n### 2) 技术路线与应用导向（3-6条，量化/推理/对齐相关请单列）")
        prompt_parts.append("\n### 3) 风险与不确定性（最多5条）")
        prompt_parts.append("\n### 4) 重点论文清单（最多5篇，仅限关注领域）")
        prompt_parts.append("- 每篇：P{n} + 1句话理由（依据：Px）")

        prompt = "\n".join(prompt_parts)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个严谨的研究分析与总结助手（V4），聚焦大模型/多模态/视觉/训练/量化/推理加速。\n"
                    "- 只使用用户提供材料，不允许臆测。\n"
                    "- 所有洞察必须给出论文编号依据；无法支持就写“材料未提供，无法判断”。\n"
                    "- 输出专业、凝练、可执行，避免空话。\n"
                    "- 严格按用户给定标题结构输出。\n\n"
                    + _FOCUS_BLOCK
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            self.logger.info(f"[batch {batch_index}/{total_batches}] 调用阿里千问API生成批量总结 (V4)...")
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.4,
                max_tokens=3000,
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            return f"# 批次 {batch_index}/{total_batches}\n\n*生成失败：{response.message}*\n"
        except Exception as e:
            self.logger.error(f"[batch {batch_index}/{total_batches}] 生成总结失败: {e}", exc_info=True)
            return f"# 批次 {batch_index}/{total_batches}\n\n*生成异常：{str(e)}*\n"
