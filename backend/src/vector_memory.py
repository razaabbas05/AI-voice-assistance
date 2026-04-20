"""
Vector Memory - Pinecone-based conversation memory
"""

import os
import hashlib
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VectorMemory:
    def __init__(self, session_id: str = "default_user"):
        """Initialize Pinecone vector memory"""
        
        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        self.index_name = "voice-assistant-memory"
        self.session_id = session_id
        self.embedding_model = "text-embedding-3-small"
        self.dimension = 1536  # Dimension for text-embedding-3-small
        
        # Create index if it doesn't exist
        self._create_index_if_not_exists()
        
        # Connect to index
        self.index = self.pc.Index(self.index_name)
        
        print(f"✅ Vector Memory initialized for session: {session_id}")
    
    def _create_index_if_not_exists(self):
        """Create Pinecone index if it doesn't exist"""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                print(f"📦 Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print("✅ Index created successfully")
        except Exception as e:
            print(f"⚠️ Index check error (might already exist): {e}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Embedding error: {e}")
            return []
    
    def _generate_id(self, text: str, timestamp: str) -> str:
        """Generate unique ID for vector"""
        unique_string = f"{self.session_id}_{timestamp}_{text[:50]}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def add_memory(self, user_message: str, assistant_response: str, emotion: str = "neutral"):
        """Store conversation exchange in vector memory"""
        
        # Combine for context
        combined_text = f"User: {user_message}\nAssistant: {assistant_response}"
        
        # Get embedding
        embedding = self._get_embedding(combined_text)
        if not embedding:
            return
        
        # Create unique ID
        import time
        timestamp = str(time.time())
        vector_id = self._generate_id(combined_text, timestamp)
        
        # Store in Pinecone with metadata
        metadata = {
            "user_message": user_message,
            "assistant_response": assistant_response,
            "emotion": emotion,
            "timestamp": timestamp,
            "session_id": self.session_id
        }
        
        try:
            self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=self.session_id
            )
            print(f"💾 Memory stored: {user_message[:30]}...")
        except Exception as e:
            print(f"❌ Error storing memory: {e}")
    
    def get_relevant_memories(self, query: str, top_k: int = 10) -> List[Dict]:
        """Retrieve relevant past conversations"""
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        try:
            # Search Pinecone
            results = self.index.query(
                namespace=self.session_id,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            memories = []
            for match in results.matches:
                # Lower threshold to get more memories
                if match.score > 0.3:
                    memories.append({
                        "user": match.metadata.get("user_message", ""),
                        "assistant": match.metadata.get("assistant_response", ""),
                        "emotion": match.metadata.get("emotion", "neutral"),
                        "relevance_score": match.score
                    })
            
            print(f"📚 Retrieved {len(memories)} relevant memories")
            return memories
            
        except Exception as e:
            print(f"❌ Error retrieving memories: {e}")
            return []
    
    def search_all_memories(self, keyword: str) -> List[Dict]:
        """Search all memories for a specific keyword"""
        query_embedding = self._get_embedding(keyword)
        if not query_embedding:
            return []
        
        try:
            results = self.index.query(
                namespace=self.session_id,
                vector=query_embedding,
                top_k=20,
                include_metadata=True
            )
            
            memories = []
            for match in results.matches:
                if match.score > 0.3:  # Even lower threshold for specific searches
                    memories.append({
                        "user": match.metadata.get("user_message", ""),
                        "assistant": match.metadata.get("assistant_response", ""),
                        "emotion": match.metadata.get("emotion", "neutral"),
                        "relevance_score": match.score
                    })
            
            return memories
        except Exception as e:
            print(f"❌ Error searching memories: {e}")
            return []
    
    def clear_memory(self):
        """Clear all memories for this session"""
        try:
            self.index.delete(delete_all=True, namespace=self.session_id)
            print(f"🧹 Memory cleared for session: {self.session_id}")
        except Exception as e:
            print(f"❌ Error clearing memory: {e}")
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        try:
            stats = self.index.describe_index_stats()
            namespace_stats = stats.namespaces.get(self.session_id, {})
            
            return {
                "total_vectors": namespace_stats.get("vector_count", 0),
                "session_id": self.session_id
            }
        except:
            return {"total_vectors": 0, "session_id": self.session_id}