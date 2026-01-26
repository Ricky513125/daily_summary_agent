"""快速启动脚本 V2 - 按关键词分别处理"""
import argparse
from main_v2 import DailySummaryAgentV2
from utils.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='每日AI总结Agent V2 - 按关键词分别处理')
    args = parser.parse_args()
    
    logger.info("启动 Daily Summary Agent V2")
    logger.info("=" * 60)
    logger.info("工作模式: 按关键词分别处理")
    logger.info("- 每个关键词单独爬取论文")
    logger.info("- 每个关键词生成单独总结")
    logger.info("- 论文PDF下载到本地")
    logger.info("=" * 60)
    
    agent = DailySummaryAgentV2()
    agent.run()


if __name__ == "__main__":
    main()
