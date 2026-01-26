"""快速启动脚本 V3 - 看N天前的文章，使用阿里千问"""
import argparse
from main_v3 import DailySummaryAgentV3
from utils.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='每日AI总结Agent V3 - 看N天前的文章')
    parser.add_argument('--days-ago', type=int, default=2, 
                       help='查看几天前的文章（默认2天前）')
    args = parser.parse_args()
    
    logger.info("启动 Daily Summary Agent V3")
    logger.info("=" * 60)
    logger.info("版本特性:")
    logger.info(f"- 查看 {args.days_ago} 天前发布的文章")
    logger.info("- 文件夹按日期组织: 日期/关键词/")
    logger.info("- 使用阿里千问生成总结")
    logger.info("- 每个关键词单独爬取和总结")
    logger.info("=" * 60)
    
    agent = DailySummaryAgentV3(days_ago=args.days_ago)
    agent.run()


if __name__ == "__main__":
    main()
