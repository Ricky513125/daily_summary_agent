"""日志工具"""
import sys
from pathlib import Path
from loguru import logger
from config import LOG_LEVEL, LOGS_DIR

# 配置日志
logger.remove()  # 移除默认处理器

# 控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True
)

# 文件输出
logger.add(
    LOGS_DIR / "agent.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=LOG_LEVEL,
    rotation="10 MB",
    retention="7 days",
    compression="zip"
)

__all__ = ["logger"]
