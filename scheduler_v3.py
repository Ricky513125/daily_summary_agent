"""定时任务调度器 V3 - 每周二至周六上午10:00运行"""
import schedule
import time
from datetime import datetime
from main_v3 import DailySummaryAgentV3
from utils.logger import logger


def run_daily_task():
    """执行每日任务"""
    try:
        logger.info("=" * 80)
        logger.info(f"定时任务启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 创建并运行Agent（抓取前一天的论文）
        agent = DailySummaryAgentV3(days_ago=1)
        agent.run()
        
        logger.info("=" * 80)
        logger.info(f"定时任务完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)


def main():
    """主函数 - 启动定时任务调度器"""
    logger.info("=" * 80)
    logger.info("Daily Summary Agent V3 - 定时任务调度器")
    logger.info("=" * 80)
    logger.info("配置: 每周二至周六 10:00 (北京时间) 自动运行")
    logger.info("功能: 爬取前一天的论文 → 生成总结 → 汇总文档 → 发送邮件")
    logger.info("说明: 此时当天的更新已经完成，抓取前一天的论文")
    logger.info("=" * 80)
    
    # 配置定时任务：每周二至周六上午10:00运行
    schedule.every().tuesday.at("10:00").do(run_daily_task)
    schedule.every().wednesday.at("10:00").do(run_daily_task)
    schedule.every().thursday.at("10:00").do(run_daily_task)
    schedule.every().friday.at("10:00").do(run_daily_task)
    schedule.every().saturday.at("10:00").do(run_daily_task)
    
    logger.info("定时任务已配置，等待执行...")
    logger.info("运行时间: 每周二至周六 10:00 (北京时间)")
    logger.info("按 Ctrl+C 停止")
    
    # 可选：立即运行一次（用于测试）
    # logger.info("\n立即运行一次（测试）...")
    # run_daily_task()
    
    # 保持运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("\n定时任务调度器已停止")


if __name__ == "__main__":
    main()
