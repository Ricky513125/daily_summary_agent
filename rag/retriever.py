"""检索器"""
from typing import List, Dict, Optional
from rag.vector_store import VectorStore
from config import TOP_K
from utils.logger import logger


class Retriever:
    """RAG检索器"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.logger = logger.bind(module="retriever")
    
    def retrieve(self, query: str, top_k: int = TOP_K, filters: Optional[Dict] = None) -> List[Dict]:
        """检索相关内容"""
        results = self.vector_store.search(query, top_k=top_k, filter_dict=filters)
        return results
    
    def retrieve_by_category(self, category: str, top_k: int = TOP_K) -> List[Dict]:
        """按类别检索"""
        query = f"关于{category}的内容"
        filters = None  # 可以根据需要添加过滤条件
        return self.retrieve(query, top_k=top_k, filters=filters)
    
    def retrieve_recent(self, days: int = 1, top_k: int = TOP_K) -> List[Dict]:
        """检索最近的内容"""
        # 这里可以根据时间过滤，需要向量数据库支持时间范围查询
        query = "最新的AI、大模型、计算机视觉相关内容"
        return self.retrieve(query, top_k=top_k)
    
    def format_results(self, results: List[Dict]) -> str:
        """格式化检索结果"""
        formatted = []
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            title = metadata.get('title', '未知标题')
            url = metadata.get('url', '')
            source = metadata.get('source', '')
            
            formatted.append(f"""
[{i}] {title}
来源: {source}
链接: {url}
内容摘要: {content[:200]}...
""")
        
        return "\n".join(formatted)
