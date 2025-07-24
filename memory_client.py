#!/usr/bin/env python3
"""
Simple memory client for PostgreSQL with pgvector
Provides basic storage and retrieval of memories with vector similarity search
"""

import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

import asyncpg
import numpy as np
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory-client")


class MemoryClient:
    """Simple memory client for vector-based memory storage"""
    
    def __init__(self, db_url: str, openai_api_key: Optional[str] = None):
        self.db_url = db_url
        self.pool = None
        self.openai_client = None
        
        # Initialize OpenAI if API key provided
        if openai_api_key or os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        else:
            logger.warning("No OpenAI API key provided - embeddings will be random")
    
    async def connect(self):
        """Connect to the database"""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10)
        logger.info("Connected to PostgreSQL")
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI or fallback to random"""
        if self.openai_client:
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
        
        # Fallback to random embedding for testing
        logger.debug("Using random embedding")
        return np.random.rand(1536).tolist()
    
    async def store_memory(self, agent_id: str, content: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> int:
        """Store a memory with its embedding"""
        embedding = self._get_embedding(content)
        
        # Convert embedding list to PostgreSQL vector format
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        query = """
        INSERT INTO memories (agent_id, content, embedding, metadata)
        VALUES ($1, $2, $3::vector, $4)
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            memory_id = await conn.fetchval(
                query, 
                agent_id, 
                content, 
                embedding_str, 
                json.dumps(metadata or {})
            )
        
        logger.info(f"Stored memory {memory_id} for agent {agent_id}")
        return memory_id
    
    async def search_memories(self, query: str, agent_id: Optional[str] = None, 
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar memories using vector similarity"""
        query_embedding = self._get_embedding(query)
        
        # Convert embedding list to PostgreSQL vector format
        query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        sql = """
        SELECT 
            id, 
            agent_id, 
            content, 
            metadata,
            created_at,
            1 - (embedding <=> $1::vector) as similarity
        FROM memories
        WHERE ($2::text IS NULL OR agent_id = $2)
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, query_embedding_str, agent_id, limit)
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "agent_id": row["agent_id"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "similarity": float(row["similarity"])
            })
        
        return results
    
    async def get_recent_memories(self, agent_id: Optional[str] = None, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memories chronologically"""
        sql = """
        SELECT id, agent_id, content, metadata, created_at
        FROM memories
        WHERE ($1::text IS NULL OR agent_id = $1)
        ORDER BY created_at DESC
        LIMIT $2
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, agent_id, limit)
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "agent_id": row["agent_id"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return results
    
    async def delete_memory(self, memory_id: int) -> bool:
        """Delete a specific memory"""
        sql = "DELETE FROM memories WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(sql, memory_id)
        
        return result == "DELETE 1"
    
    async def clear_agent_memories(self, agent_id: str) -> int:
        """Clear all memories for a specific agent"""
        sql = "DELETE FROM memories WHERE agent_id = $1"
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(sql, agent_id)
        
        # Extract count from result
        count = int(result.split()[1])
        logger.info(f"Cleared {count} memories for agent {agent_id}")
        return count


# Example usage and testing
async def test_memory_client():
    """Test the memory client"""
    db_url = "postgresql://superagent:superagent@localhost:5433/superagent"
    
    async with MemoryClient(db_url) as client:
        print("🧠 Testing Memory Client...")
        print("-" * 50)
        
        # Store some memories
        agent_id = "test-agent"
        
        memories = [
            "The user's name is John and he likes Python programming",
            "John is working on a Discord bot project",
            "The Discord bot needs to handle memory and context",
            "John prefers async Python code with type hints"
        ]
        
        print("📝 Storing memories...")
        for memory in memories:
            memory_id = await client.store_memory(
                agent_id, 
                memory,
                metadata={"source": "test", "timestamp": datetime.utcnow().isoformat()}
            )
            print(f"  Stored: {memory[:50]}... (ID: {memory_id})")
        
        # Search memories
        print("\n🔍 Searching memories...")
        query = "What programming language does the user prefer?"
        results = await client.search_memories(query, agent_id=agent_id)
        
        print(f"Query: {query}")
        print("Results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['content'][:60]}...")
            print(f"     Similarity: {result['similarity']:.3f}")
        
        # Get recent memories
        print("\n📅 Recent memories:")
        recent = await client.get_recent_memories(agent_id, limit=3)
        for memory in recent:
            print(f"  - {memory['content'][:60]}...")
            print(f"    Created: {memory['created_at']}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_memory_client())