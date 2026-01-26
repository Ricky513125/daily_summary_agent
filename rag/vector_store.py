"""向量数据库"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from config import VECTOR_DB_PATH, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
from utils.logger import logger
from crawlers.base_crawler import Article


class VectorStore:
    """向量数据库管理器"""
    
    def __init__(self, collection_name: str = "articles"):
        self.collection_name = collection_name
        self.logger = logger.bind(module="vector_store")
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 初始化嵌入模型
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.logger.info(f"向量数据库初始化完成，使用模型: {EMBEDDING_MODEL}")
    
    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """将文本分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def add_articles(self, articles: List[Article]):
        """添加文章到向量数据库"""
        if not articles:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for article in articles:
            # 将文章内容分块
            chunks = self.chunk_text(article.content)
            
            for i, chunk in enumerate(chunks):
                # 生成文档ID
                doc_id = f"{article.url}_{i}"
                
                # 准备元数据
                metadata = {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "publish_time": article.publish_time.isoformat() if article.publish_time else "",
                    "author": article.author or "",
                    "chunk_index": str(i),
                    "total_chunks": str(len(chunks))
                }
                
                documents.append(chunk)
                metadatas.append(metadata)
                ids.append(doc_id)
        
        # 批量添加
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            self.logger.info(f"添加 {len(articles)} 篇文章，共 {len(documents)} 个块到向量数据库")
    
    def search(self, query: str, top_k: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """搜索相似内容"""
        # 生成查询向量
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # 构建查询
        where = filter_dict if filter_dict else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        # 格式化结果
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        self.logger.info(f"搜索 '{query}' 返回 {len(formatted_results)} 个结果")
        return formatted_results
    
    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_documents": count
        }
