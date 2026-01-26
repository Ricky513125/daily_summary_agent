"""定时任务调度器 V3 - 每天7:00运行"""
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
        
        # 创建并运行Agent
        agent = DailySummaryAgentV3()
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
    logger.info("配置: 每天 07:00 自动运行")
    logger.info("功能: 爬取论文 → 生成总结 → 汇总文档 → 发送邮件")
    logger.info("=" * 80)
    
    # 配置定时任务：每天7:00运行
    schedule.every().day.at("07:00").do(run_daily_task)
    
    logger.info("定时任务已配置，等待执行...")
    logger.info("下次运行时间: 明天 07:00")
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
