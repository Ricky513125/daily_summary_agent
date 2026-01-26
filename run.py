"""快速启动脚本"""
import argparse
from main import DailySummaryAgent
from utils.logger import logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="每日AI总结Agent")
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="不使用RAG，直接生成总结"
    )
    parser.add_argument(
        "--time",
        type=str,
        help="指定执行时间（格式：HH:MM），用于测试定时任务"
    )
    
    args = parser.parse_args()
    
    agent = DailySummaryAgent()
    agent.run(use_rag=not args.no_rag)


if __name__ == "__main__":
    main()
