"""快速启动脚本 V5 - 无 PDF 下载，逐篇 LLM 短摘要，无批量/每日汇总，发邮件。"""
import argparse
from main_v5 import DailySummaryAgentV5
from config_v4 import KEYWORDS_V4, EXCLUDE_CATEGORIES_V4, EXCLUDE_KEYWORDS_V4
from utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description="每日AI总结Agent V5 - 统计文献数 + 发邮件")
    parser.add_argument("--days-ago", type=int, default=1, help="查看几天前的文章（默认1天前）")
    args = parser.parse_args()

    logger.info("启动 Daily Summary Agent V5")
    logger.info("=" * 60)
    logger.info("版本特性:")
    logger.info(f"- 查看 {args.days_ago} 天前发布的文章")
    logger.info(f"- 关键词数: {len(KEYWORDS_V4)}")
    logger.info(f"- 排除分类: {EXCLUDE_CATEGORIES_V4}")
    logger.info(f"- 排除关键词数: {len(EXCLUDE_KEYWORDS_V4)}")
    logger.info("- 无 PDF 下载，逐篇 LLM 短摘要，无批量/每日汇总")
    logger.info("=" * 60)

    agent = DailySummaryAgentV5(days_ago=args.days_ago)
    agent.run()


if __name__ == "__main__":
    main()
