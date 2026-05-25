"""快速启动脚本 V4 - 在 V3 基础上扩展量化关键词并剔除机器人/医学/安全领域。"""
import argparse
from main_v4 import DailySummaryAgentV4
from config_v4 import KEYWORDS_V4, EXCLUDE_CATEGORIES_V4, EXCLUDE_KEYWORDS_V4
from utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description='每日AI总结Agent V4 - 量化关键词 + 领域过滤')
    parser.add_argument('--days-ago', type=int, default=1,
                        help='查看几天前的文章（默认1天前）')
    args = parser.parse_args()

    logger.info("启动 Daily Summary Agent V4")
    logger.info("=" * 60)
    logger.info("版本特性:")
    logger.info(f"- 查看 {args.days_ago} 天前发布的文章")
    logger.info(f"- 关键词数: {len(KEYWORDS_V4)}（已扩充量化相关）")
    logger.info(f"- 排除分类: {EXCLUDE_CATEGORIES_V4}")
    logger.info(f"- 排除关键词数: {len(EXCLUDE_KEYWORDS_V4)}（机器人硬件/医学/安全）")
    logger.info("- 提示词聚焦：LLM/多模态/视觉/训练/量化/推理加速")
    logger.info("=" * 60)

    agent = DailySummaryAgentV4(days_ago=args.days_ago)
    agent.run()


if __name__ == "__main__":
    main()
