"""定时任务调度器"""
import schedule
import time
from main import DailySummaryAgent
from utils.logger import logger


def run_daily_summary():
    """运行每日总结任务"""
    logger.info("定时任务触发：开始执行每日总结")
    try:
        agent = DailySummaryAgent()
        agent.run(use_rag=True)
        logger.info("定时任务执行完成")
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)


def main():
    """主函数"""
    logger.info("启动定时任务调度器")
    
    # 每天上午9点执行
    schedule.every().day.at("09:00").do(run_daily_summary)
    
    # 也可以每小时执行（用于测试）
    # schedule.every().hour.do(run_daily_summary)
    
    # 或者每天特定时间执行
    # schedule.every().day.at("09:00").do(run_daily_summary)
    # schedule.every().day.at("18:00").do(run_daily_summary)
    
    logger.info("定时任务已设置：每天 09:00 执行")
    logger.info("按 Ctrl+C 退出")
    
    # 运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("定时任务调度器已停止")
