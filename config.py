"""配置文件"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
VECTOR_DB_DIR = DATA_DIR / "vector_db"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"

# 创建必要的目录
for dir_path in [DATA_DIR, VECTOR_DB_DIR, LOGS_DIR, OUTPUT_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 可选: deepseek-chat, deepseek-coder
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 向量数据库配置
VECTOR_DB_PATH = str(VECTOR_DB_DIR)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 爬虫配置
WECHAT_ACCOUNTS = os.getenv("WECHAT_ACCOUNTS", "").split(",") if os.getenv("WECHAT_ACCOUNTS") else []
ARCHIVE_URLS = os.getenv("ARCHIVE_URLS", "").split(",") if os.getenv("ARCHIVE_URLS") else []

# 内容过滤关键词
KEYWORDS = os.getenv("KEYWORDS", "大模型,AI,人工智能,计算机视觉,深度学习,机器学习,LLM,GPT,transformer").split(",")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = str(LOGS_DIR / "agent.log")

# RAG配置
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "10"))

# 爬虫配置
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", "30"))
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "50"))
